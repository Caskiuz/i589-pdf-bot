"""Extracción por secciones con DeepSeek (function calling estricto + fallback JSON).

El I-589 tiene muchos datos; para no truncar la salida ni saturar el schema,
se extrae en 4 llamadas independientes (solicitante, familia, antecedentes,
solicitud/preguntas). Cada llamada usa un tool con schema JSON estricto
generado desde los modelos Pydantic, y reintenta hasta 2 veces si la
validación falla. Si el modo estricto no es aceptado por la API, se cae al
modo JSON clásico con el schema embebido en el prompt.
"""
from __future__ import annotations

import json
import logging

import openai
from pydantic import BaseModel, ValidationError

from ..schemas.i589 import (
    Address,
    Applicant,
    Basis,
    Child,
    Education,
    Employment,
    I589Data,
    Questions,
    Relative,
    Spouse,
)
from .client import get_client, get_model

log = logging.getLogger(__name__)

MAX_SOURCE_CHARS = 40000
MAX_RETRIES = 2


class FamilySection(BaseModel):
    spouse: Spouse | None = None
    has_children: bool | None = None
    total_children: str = ""
    children: list[Child] = []


class BackgroundSection(BaseModel):
    addresses_abroad: list[Address] = []
    residences: list[Address] = []
    education: list[Education] = []
    employment: list[Employment] = []
    mother: Relative = Relative()
    father: Relative = Relative()
    siblings: list[Relative] = []


class ClaimSection(BaseModel):
    basis: Basis = Basis()
    questions: Questions = Questions()
    narrative: str = ""


SYSTEM_PROMPT = (
    "Eres un asistente de un despacho de inmigración en Estados Unidos. Tu tarea es "
    "extraer datos del texto de una conversación de WhatsApp entre un cliente y un "
    "preparador de formularios migratorios, para llenar el Formulario I-589 (solicitud "
    "de asilo).\n"
    "REGLA DE IDIOMA (CRÍTICA): USCIS exige el formulario completado en INGLÉS. Todos los "
    "valores que devuelvas deben estar en inglés: traduce países, ciudades (si tienen "
    "nombre en inglés: Mexico, United States, Spain...), ocupaciones, religiones, grupos "
    "étnicos, estatus migratorios, explicaciones y la narrativa. Los nombres propios de "
    "personas y las direcciones se dejan tal cual (sin traducir). La narrativa debe ser "
    "una declaración en primera persona, en inglés natural y profesional.\n"
    "REGLAS ESTRICTAS:\n"
    "1. Extrae SOLO información del SOLICITANTE de asilo (no del preparador).\n"
    "2. El texto es desordenado e informal: normaliza nombres, fechas y direcciones.\n"
    "3. Fechas en formato YYYY-MM-DD cuando se conozca el día; MM/YYYY si solo se "
    "conoce el mes; cadena vacía \"\" si no se menciona.\n"
    "4. NUNCA inventes datos. Si un dato no está en el texto, deja el campo vacío "
    "(\"\" para texto, null para opciones booleanas).\n"
    "5. Nombres con iniciales en mayúscula.\n"
    "6. Si el texto menciona varios valores (p. ej. varias direcciones o empleos), "
    "inclúyelos todos como elementos de la lista, el más reciente primero.\n"
    "7. Usa EXACTAMENTE estos códigos: sexo \"M\" o \"F\"; estado civil \"single\", "
    "\"married\", \"divorced\" o \"widowed\"; corte de inmigración \"never\" (nunca), "
    "\"now\" (ahora) o \"not_now\" (ya no).\n"
    "8. Responde SIEMPRE con la estructura de datos solicitada."
)


def _inline_schema(schema: dict) -> dict:
    """Resuelve $defs/$ref en línea (requerido por el modo estricto de DeepSeek)."""
    defs = schema.pop("$defs", {})

    def resolve(node):
        if isinstance(node, dict):
            if "$ref" in node and node["$ref"].startswith("#/$defs/"):
                return resolve(defs[node["$ref"].split("/")[-1]])
            return {k: resolve(v) for k, v in node.items() if k not in ("title", "default")}
        if isinstance(node, list):
            return [resolve(x) for x in node]
        return node

    return resolve(schema)


def _strictify(schema: dict) -> dict:
    """Convierte el schema Pydantic a la forma exigida por el modo estricto:
    - $defs resueltos en línea, sin title/default
    - additionalProperties: false en todos los objetos
    - todas las propiedades declaradas en required
    """
    schema = _inline_schema(json.loads(json.dumps(schema)))

    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "object" or "properties" in node:
                node.setdefault("additionalProperties", False)
                props = node.get("properties") or {}
                node["properties"] = props
                node["required"] = list(props.keys())
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(schema)
    return schema


def _build_tool(tool_name: str, model: type[BaseModel], description: str) -> dict:
    return {
        "type": "function",
        "function": {
            "name": tool_name,
            "description": description,
            "parameters": _strictify(model.model_json_schema()),
            "strict": True,
        },
    }


def _extract_section(
    text: str,
    tool_name: str,
    model: type[BaseModel],
    description: str,
) -> BaseModel:
    client = get_client()
    base_messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": text[:MAX_SOURCE_CHARS]},
    ]

    # --- Estrategia 1: function calling estricto ---
    messages = list(base_messages)
    last_error = ""
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = client.chat.completions.create(
                model=get_model(),
                messages=messages,
                tools=[_build_tool(tool_name, model, description)],
                tool_choice={"type": "function", "function": {"name": tool_name}},
                temperature=0.1,
                max_tokens=8000,
            )
            msg = resp.choices[0].message
            if not msg.tool_calls:
                raise ValueError("el modelo no llamó a la función")
            args = json.loads(msg.tool_calls[0].function.arguments)
            return model.model_validate(args)
        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            last_error = str(exc)[:1200]
            log.warning("sección %s (tools) intento %d inválido: %s", tool_name, attempt + 1, last_error[:200])
            messages.append({"role": "assistant", "content": "(intento previo)"})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"Tu respuesta anterior no pasó la validación: {last_error}\n"
                        "Devuelve la estructura de nuevo con los datos corregidos. "
                        'Usa "" para texto vacío y null para booleanos no mencionados.'
                    ),
                }
            )
        except openai.OpenAIError as exc:
            last_error = f"API: {exc}"
            log.warning("sección %s (tools) error de API: %s", tool_name, exc)
            break  # pasar al fallback JSON

    # --- Estrategia 2: modo JSON con el schema embebido en el prompt ---
    schema_json = json.dumps(_strictify(model.model_json_schema()), ensure_ascii=False)
    messages = list(base_messages) + [
        {
            "role": "user",
            "content": (
                "Devuelve ÚNICAMENTE un objeto JSON válido que cumpla exactamente este "
                f"esquema (todas las claves obligatorias):\n{schema_json}"
            ),
        }
    ]
    last_error = ""
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = client.chat.completions.create(
                model=get_model(),
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=8000,
            )
            raw = resp.choices[0].message.content or ""
            start, end = raw.find("{"), raw.rfind("}")
            args = json.loads(raw[start : end + 1])
            return model.model_validate(args)
        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            last_error = str(exc)[:1200]
            messages.append(
                {
                    "role": "user",
                    "content": f"El JSON anterior falló la validación: {last_error}. Corrige y devuelve el JSON completo.",
                }
            )
        except openai.OpenAIError as exc:
            last_error = f"API: {exc}"
            break
    raise RuntimeError(f"No se pudo extraer la sección '{tool_name}': {last_error}")


def extract_all(text: str) -> I589Data:
    """Extrae todas las secciones del texto fuente y arma el I589Data completo."""
    applicant = _extract_section(
        text,
        "fill_applicant",
        Applicant,
        "Datos biográficos del solicitante de asilo, contactos, entrada a EE. UU. y pasaporte (Parte A.I del I-589).",
    )
    family = _extract_section(
        text,
        "fill_family",
        FamilySection,
        "Cónyuge e hijos del solicitante (Parte A.II del I-589), incluido si tiene hijos y cuántos.",
    )
    background = _extract_section(
        text,
        "fill_background",
        BackgroundSection,
        "Antecedentes (Parte A.III): direcciones (últimas en el extranjero y últimos 5 años), educación, empleo y padres/hermanos.",
    )
    claim = _extract_section(
        text,
        "fill_claim",
        ClaimSection,
        "Base de la solicitud de asilo (Parte B: motivos y preguntas sí/no con explicaciones), preguntas de la Parte C y la narrativa/declaración de persecución.",
    )

    assert isinstance(applicant, Applicant)
    assert isinstance(family, FamilySection)
    assert isinstance(background, BackgroundSection)
    assert isinstance(claim, ClaimSection)

    data = I589Data(
        applicant=applicant,
        spouse=family.spouse,
        has_children=family.has_children,
        total_children=family.total_children,
        children=family.children,
        addresses_abroad=background.addresses_abroad,
        residences=background.residences,
        education=background.education,
        employment=background.employment,
        mother=background.mother,
        father=background.father,
        siblings=background.siblings,
        basis=claim.basis,
        questions=claim.questions,
        narrative=claim.narrative,
        source_text=text,
    )
    # Derivación: nombre impreso de la firma = nombre completo del solicitante
    data.signature.print_name = (
        f"{applicant.first_name} {applicant.middle_name} {applicant.last_name}"
        .replace("  ", " ")
        .strip()
    )
    # Derivación: volcar los alias extraídos al campo editable "otros nombres usados"
    if not data.applicant.other_names:
        data.applicant.other_names = "; ".join(
            f"{al.first_name} {al.middle_name} {al.last_name}".replace("  ", " ").strip()
            for al in data.applicant.aliases
            if any([al.first_name, al.last_name, al.middle_name])
        )
    return data
