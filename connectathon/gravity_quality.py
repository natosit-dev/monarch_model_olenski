from __future__ import annotations

from typing import Any, Mapping

from connectathon.preflight import preflight_bundle
from connectathon.gravity_materialize import bundle_resources, observation_by_loinc
from connectathon.gravity_questionnaire import (
    DEFAULT_CURRENCY,
    HEART_RATE_LOINC,
    ISO_4217_SYSTEM,
    PAIN_LOINC,
    PHQ2_TOTAL,
    PHQ_SCORE_BY_CODE,
    RXNORM_SYSTEM,
    UCUM_SYSTEM,
)
from connectathon.gravity_response import (
    answer_absent_reason,
    find_response_items,
    first_answer,
    iter_response_items,
)
from monarch.questionnaire.definitions import (
    SCOPE_EXTENSION_URL,
    enable_when_satisfied,
    extension_value,
    quantity_unit,
)
from monarch.questionnaire.scope import SCOPE_ORDER


def _quantity(resource: Mapping[str, Any], link_id: str) -> Mapping[str, Any] | None:
    answer = first_answer(resource, link_id)
    quantity = answer.get("valueQuantity") if isinstance(answer, Mapping) else None
    return quantity if isinstance(quantity, Mapping) else None


def _quantity_value(resource: Mapping[str, Any], link_id: str) -> float | None:
    quantity = _quantity(resource, link_id)
    value = quantity.get("value") if quantity else None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _integer_value(resource: Mapping[str, Any], link_id: str) -> int | None:
    answer = first_answer(resource, link_id)
    value = answer.get("valueInteger") if isinstance(answer, Mapping) else None
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def _coding_value(resource: Mapping[str, Any], link_id: str) -> Mapping[str, Any] | None:
    answer = first_answer(resource, link_id)
    coding = answer.get("valueCoding") if isinstance(answer, Mapping) else None
    return coding if isinstance(coding, Mapping) else None


def _coding_values(resource: Mapping[str, Any], link_id: str) -> list[Mapping[str, Any]]:
    items = find_response_items(resource, link_id)
    if not items:
        return []
    values: list[Mapping[str, Any]] = []
    for answer in items[0].get("answer", []) or []:
        if not isinstance(answer, Mapping):
            continue
        coding = answer.get("valueCoding")
        if isinstance(coding, Mapping):
            values.append(coding)
    return values


def _boolean_value(resource: Mapping[str, Any], link_id: str) -> bool | None:
    answer = first_answer(resource, link_id)
    value = answer.get("valueBoolean") if isinstance(answer, Mapping) else None
    return value if isinstance(value, bool) else None


def _string_value(resource: Mapping[str, Any], link_id: str) -> str | None:
    answer = first_answer(resource, link_id)
    value = answer.get("valueString") if isinstance(answer, Mapping) else None
    return str(value) if value is not None else None


def _questionnaire_index(questionnaire: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}

    def walk(items: list[Mapping[str, Any]], inherited_scope: str | None = None) -> None:
        for item in items:
            link_id = str(item.get("linkId") or "")
            if not link_id:
                continue
            own_scope = extension_value(item, SCOPE_EXTENSION_URL)
            effective_scope = str(own_scope or inherited_scope) if (own_scope or inherited_scope) else None
            index[link_id] = {"item": item, "min_scope": effective_scope}
            children = [child for child in item.get("item", []) or [] if isinstance(child, Mapping)]
            if children:
                walk(children, effective_scope)

    walk([item for item in questionnaire.get("item", []) or [] if isinstance(item, Mapping)])
    return index


def _scope_allows_minimum(minimum: str | None, selected_scope: str) -> bool:
    if not minimum:
        return True
    try:
        return SCOPE_ORDER.index(selected_scope) >= SCOPE_ORDER.index(minimum)
    except ValueError:
        return False


def _answer_signature(answer: Mapping[str, Any]) -> tuple[Any, ...] | None:
    if isinstance(answer.get("valueCoding"), Mapping):
        coding = answer["valueCoding"]
        return ("valueCoding", coding.get("system"), coding.get("code"))
    for key in ("valueString", "valueInteger", "valueDecimal", "valueBoolean"):
        if key in answer:
            return (key, answer.get(key))
    return None


def _allowed_option_signatures(item: Mapping[str, Any]) -> set[tuple[Any, ...]]:
    signatures: set[tuple[Any, ...]] = set()
    for option in item.get("answerOption", []) or []:
        if isinstance(option, Mapping):
            signature = _answer_signature(option)
            if signature is not None:
                signatures.add(signature)
    return signatures


def _expected_value_keys(item_type: str) -> set[str]:
    return {
        "string": {"valueString"},
        "text": {"valueString"},
        "integer": {"valueInteger"},
        "decimal": {"valueDecimal"},
        "quantity": {"valueQuantity"},
        "boolean": {"valueBoolean"},
        "choice": {"valueCoding", "valueString", "valueInteger", "valueDecimal"},
    }.get(item_type, set())


def _response_scalar_map(response: Mapping[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for _path, item in iter_response_items(list(response.get("item") or [])):
        link_id = str(item.get("linkId") or "")
        answers = [answer for answer in item.get("answer", []) or [] if isinstance(answer, Mapping)]
        parsed: list[Any] = []
        for answer in answers:
            if answer_absent_reason(answer):
                continue
            if isinstance(answer.get("valueCoding"), Mapping):
                parsed.append(answer["valueCoding"].get("code"))
            elif "valueBoolean" in answer:
                parsed.append(answer.get("valueBoolean"))
            elif "valueString" in answer:
                parsed.append(answer.get("valueString"))
            elif "valueInteger" in answer:
                parsed.append(answer.get("valueInteger"))
            elif "valueDecimal" in answer:
                parsed.append(answer.get("valueDecimal"))
            elif isinstance(answer.get("valueQuantity"), Mapping):
                parsed.append(answer["valueQuantity"].get("value"))
        if parsed:
            values[link_id] = parsed if len(parsed) > 1 else parsed[0]
    return values


def _definition_conformance(
    questionnaire: Mapping[str, Any],
    response: Mapping[str, Any],
    selected_scope: str | None,
) -> tuple[list[str], list[str], list[str]]:
    index = _questionnaire_index(questionnaire)
    response_values = _response_scalar_map(response)
    conformance_errors: list[str] = []
    scope_errors: list[str] = []
    enable_when_errors: list[str] = []

    seen_links: set[str] = set()
    for path, response_item in iter_response_items(list(response.get("item") or [])):
        link_id = str(response_item.get("linkId") or "")
        seen_links.add(link_id)
        definition_entry = index.get(link_id)
        if not definition_entry:
            conformance_errors.append(f"{path}: linkId not present in Questionnaire")
            continue

        definition = definition_entry["item"]
        minimum = definition_entry["min_scope"]
        if selected_scope and not _scope_allows_minimum(minimum, selected_scope):
            scope_errors.append(f"{path}: minimum_scope={minimum}; selected_scope={selected_scope}")

        if definition.get("enableWhen") and not enable_when_satisfied(definition, response_values):
            enable_when_errors.append(f"{path}: present while enableWhen is false")

        answers = [answer for answer in response_item.get("answer", []) or [] if isinstance(answer, Mapping)]
        if definition.get("type") == "group":
            if answers:
                conformance_errors.append(f"{path}: group item must not contain direct answers")
            continue

        if definition.get("required") and not answers:
            conformance_errors.append(f"{path}: required item has no answer")

        if len(answers) > 1 and not definition.get("repeats"):
            conformance_errors.append(f"{path}: multiple answers on non-repeating item")

        expected_keys = _expected_value_keys(str(definition.get("type") or ""))
        allowed_options = _allowed_option_signatures(definition)

        for answer in answers:
            reason = answer_absent_reason(answer)
            if reason:
                continue

            value_keys = {key for key in answer if key.startswith("value")}
            if expected_keys and not (value_keys & expected_keys):
                conformance_errors.append(
                    f"{path}: expected one of {sorted(expected_keys)}, found {sorted(value_keys)}"
                )
                continue

            if allowed_options:
                signature = _answer_signature(answer)
                if signature not in allowed_options:
                    conformance_errors.append(f"{path}: answer is not one of the Questionnaire answerOption values")

            if definition.get("type") == "quantity":
                quantity = answer.get("valueQuantity")
                expected_unit = quantity_unit(definition)
                if isinstance(quantity, Mapping) and isinstance(expected_unit, Mapping):
                    for field in ("system", "code"):
                        if expected_unit.get(field) and quantity.get(field) != expected_unit.get(field):
                            conformance_errors.append(
                                f"{path}: quantity {field}={quantity.get(field)!r}; expected={expected_unit.get(field)!r}"
                            )

    for link_id, entry in index.items():
        item = entry["item"]
        if not item.get("required"):
            continue
        minimum = entry["min_scope"]
        if selected_scope and not _scope_allows_minimum(minimum, selected_scope):
            continue
        if link_id not in seen_links:
            conformance_errors.append(f"{link_id}: required item missing from QuestionnaireResponse")

    return conformance_errors, scope_errors, enable_when_errors


def caregiver_quality_gate(bundle: Mapping[str, Any]) -> dict[str, Any]:
    """Validate Monarch capture semantics plus the existing caregiver baseline projections.

    The gate intentionally avoids aggregate scoring. It checks whether the captured response
    conforms to its Questionnaire, preserves important distinctions, uses the expected units,
    and still materializes the established caregiver clinical facts without inventing new ones.
    """
    checks: list[dict[str, str]] = []

    def record(name: str, status: str, detail: str) -> None:
        checks.append({"check": name, "status": status, "detail": detail})

    structural = preflight_bundle(dict(bundle))
    record(
        "bundle.preflight",
        "PASS" if structural.get("status") == "PASS" else "FAIL",
        str(structural.get("claim") or ""),
    )

    patients = bundle_resources(bundle, "Patient")
    questionnaires = bundle_resources(bundle, "Questionnaire")
    responses = bundle_resources(bundle, "QuestionnaireResponse")
    record("patient.exists", "PASS" if len(patients) == 1 else "FAIL", f"patients={len(patients)}")
    record(
        "questionnaire.exists",
        "PASS" if len(questionnaires) == 1 else "FAIL",
        f"questionnaires={len(questionnaires)}",
    )
    record(
        "questionnaire_response.exists",
        "PASS" if len(responses) == 1 else "FAIL",
        f"responses={len(responses)}",
    )

    if not responses:
        return {
            "status": "FAIL",
            "scope": "MONARCH_CAPTURE_AND_CAREGIVER_BASELINE",
            "claim": "QuestionnaireResponse is missing; Monarch capture cannot be evaluated.",
            "checks": checks,
            "structural": structural,
        }

    response = responses[0]
    questionnaire = questionnaires[0] if questionnaires else {}

    record(
        "response.authored",
        "PASS" if response.get("authored") else "FAIL",
        f"authored={response.get('authored')!r}",
    )
    record(
        "response.status",
        "PASS" if response.get("status") == "completed" else "FAIL",
        f"status={response.get('status')!r}; partial completion remains roadmap",
    )

    expected_canonical = None
    if questionnaire:
        expected_canonical = str(questionnaire.get("url") or "")
        if questionnaire.get("version"):
            expected_canonical += f"|{questionnaire['version']}"
    record(
        "response.questionnaire_canonical",
        "PASS" if expected_canonical and response.get("questionnaire") == expected_canonical else "FAIL",
        f"response={response.get('questionnaire')!r}; questionnaire={expected_canonical!r}",
    )

    patient_full_urls = {
        entry.get("fullUrl")
        for entry in bundle.get("entry", []) or []
        if isinstance(entry, Mapping)
        and isinstance(entry.get("resource"), Mapping)
        and entry["resource"].get("resourceType") == "Patient"
    }
    subject = (response.get("subject") or {}).get("reference")
    record(
        "response.subject",
        "PASS" if subject in patient_full_urls else "FAIL",
        f"subject={subject!r}",
    )

    response_errors: list[str] = []
    for path, item in iter_response_items(list(response.get("item") or [])):
        for answer in item.get("answer", []) or []:
            reason = answer_absent_reason(answer if isinstance(answer, Mapping) else None)
            if reason in {"error", "not-a-number", "negative-infinity", "positive-infinity"}:
                response_errors.append(f"{path}:{reason}")
    record(
        "response.parse_errors",
        "FAIL" if response_errors else "PASS",
        "none" if not response_errors else ", ".join(response_errors),
    )

    scope_coding = _coding_value(response, "assessment-scope")
    selected_scope = str(scope_coding.get("code")) if scope_coding and scope_coding.get("code") else None
    scope_valid = selected_scope in SCOPE_ORDER
    record(
        "scope.selection",
        "PASS" if scope_valid else "FAIL",
        f"selected_scope={selected_scope!r}",
    )

    conformance_errors: list[str] = []
    scope_errors: list[str] = []
    enable_when_errors: list[str] = []
    if questionnaire:
        conformance_errors, scope_errors, enable_when_errors = _definition_conformance(
            questionnaire,
            response,
            selected_scope if scope_valid else None,
        )
    record(
        "questionnaire_response.definition_conformance",
        "FAIL" if conformance_errors else "PASS",
        "none" if not conformance_errors else "; ".join(conformance_errors),
    )
    record(
        "scope.content",
        "FAIL" if scope_errors else ("PASS" if scope_valid else "SKIP"),
        "none" if not scope_errors else "; ".join(scope_errors),
    )
    record(
        "enable_when.consistency",
        "FAIL" if enable_when_errors else "PASS",
        "none" if not enable_when_errors else "; ".join(enable_when_errors),
    )

    financial_codes: dict[str, str | None] = {}
    financial_invalid = False
    for link_id in (
        "financial-unexpected-100",
        "financial-unexpected-500",
        "financial-miss-week-work",
        "financial-healthcare-cost-difficulty",
        "financial-debt-affects-care",
    ):
        answer = first_answer(response, link_id)
        reason = answer_absent_reason(answer)
        coding = _coding_value(response, link_id)
        code = str(coding.get("code")) if coding and coding.get("code") else None
        financial_codes[link_id] = code or reason
        if reason and reason != "asked-declined":
            financial_invalid = True
        if code and code not in {"yes", "no", "unsure"}:
            financial_invalid = True
    record(
        "financial.choice_semantics",
        "FAIL" if financial_invalid else ("PASS" if any(financial_codes.values()) else "SKIP"),
        str(financial_codes),
    )

    money_details: list[str] = []
    money_invalid = False
    money_seen = False
    for link_id in ("financial-current-savings", "financial-current-debt"):
        answer = first_answer(response, link_id)
        reason = answer_absent_reason(answer)
        quantity = _quantity(response, link_id)
        if reason == "asked-declined":
            money_seen = True
            money_details.append(f"{link_id}=declined")
            continue
        if reason:
            money_invalid = True
            money_seen = True
            money_details.append(f"{link_id}=data-absent-reason:{reason}")
            continue
        if not quantity:
            continue
        money_seen = True
        value = quantity.get("value")
        valid = (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and value >= 0
            and quantity.get("system") == ISO_4217_SYSTEM
            and quantity.get("code") == DEFAULT_CURRENCY
        )
        money_invalid = money_invalid or not valid
        money_details.append(
            f"{link_id}={value!r} {quantity.get('code')!r} system={quantity.get('system')!r}"
        )
    record(
        "financial.currency",
        "FAIL" if money_invalid else ("PASS" if money_seen else "SKIP"),
        "; ".join(money_details) if money_details else "unanswered",
    )

    care_answer = first_answer(response, "care-hours-per-day")
    care_reason = answer_absent_reason(care_answer)
    care_quantity = _quantity(response, "care-hours-per-day")
    if care_reason == "asked-declined":
        record("care_hours.unit_plausibility", "PASS", "declined")
    elif care_reason:
        record("care_hours.unit_plausibility", "FAIL", f"data-absent-reason={care_reason}")
    elif not care_quantity:
        record("care_hours.unit_plausibility", "SKIP", "unanswered")
    else:
        value = care_quantity.get("value")
        valid = (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and 0 <= value <= 24
            and care_quantity.get("system") == UCUM_SYSTEM
            and care_quantity.get("code") == "h/d"
        )
        record(
            "care_hours.unit_plausibility",
            "PASS" if valid else "FAIL",
            f"value={value!r}; unit={care_quantity.get('unit')!r}; code={care_quantity.get('code')!r}",
        )

    safe_mode_answer = first_answer(response, "safe-absence-mode")
    safe_mode_reason = answer_absent_reason(safe_mode_answer)
    safe_mode_coding = _coding_value(response, "safe-absence-mode")
    safe_mode = str(safe_mode_coding.get("code")) if safe_mode_coding and safe_mode_coding.get("code") else None
    safe_hours_answer = first_answer(response, "safe-absence-hours")
    safe_hours_reason = answer_absent_reason(safe_hours_answer)
    safe_hours = _quantity(response, "safe-absence-hours")
    safe_invalid = False
    if safe_mode_reason and safe_mode_reason != "asked-declined":
        safe_invalid = True
    elif safe_mode == "hours":
        value = safe_hours.get("value") if safe_hours else None
        safe_invalid = not (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and value >= 0
            and safe_hours.get("system") == UCUM_SYSTEM
            and safe_hours.get("code") == "h"
        )
    elif safe_mode in {"unsure", "varies"} or safe_mode_reason == "asked-declined" or safe_mode is None:
        if safe_hours is not None or (safe_hours_reason and safe_hours_reason != "asked-declined"):
            safe_invalid = True
    else:
        safe_invalid = True
    record(
        "safe_absence.consistency",
        "FAIL" if safe_invalid else ("PASS" if safe_mode or safe_mode_reason else "SKIP"),
        f"mode={safe_mode or safe_mode_reason!r}; hours={safe_hours}",
    )

    home_codings = _coding_values(response, "home-safety")
    home_codes = [str(coding.get("code")) for coding in home_codings if coding.get("code")]
    home_other_answer = first_answer(response, "home-safety-other")
    home_other_reason = answer_absent_reason(home_other_answer)
    home_other_text = _string_value(response, "home-safety-other")
    home_invalid = False
    if "none" in home_codes and len(home_codes) > 1:
        home_invalid = True
    if "unsure" in home_codes and len(home_codes) > 1:
        home_invalid = True
    if "other" in home_codes and not (home_other_text or home_other_reason == "asked-declined"):
        home_invalid = True
    if "other" not in home_codes and (home_other_text or home_other_reason):
        home_invalid = True
    record(
        "home_safety.semantics",
        "FAIL" if home_invalid else ("PASS" if home_codes or home_other_reason else "SKIP"),
        f"codes={home_codes}; other_text_present={bool(home_other_text)}; other_reason={home_other_reason!r}",
    )

    preference_codes: dict[str, str | None] = {}
    preference_invalid = False
    for link_id, allowed in (
        ("support-person", {"yes", "no", "unsure"}),
        ("stop-return-preference", {"continue", "pause", "stop", "unsure"}),
    ):
        answer = first_answer(response, link_id)
        reason = answer_absent_reason(answer)
        coding = _coding_value(response, link_id)
        code = str(coding.get("code")) if coding and coding.get("code") else None
        preference_codes[link_id] = code or reason
        if reason and reason != "asked-declined":
            preference_invalid = True
        if code and code not in allowed:
            preference_invalid = True
    record(
        "interaction.preference_semantics",
        "FAIL" if preference_invalid else ("PASS" if any(preference_codes.values()) else "SKIP"),
        str(preference_codes),
    )

    context_answer = first_answer(response, "context-artifact-text")
    context_reason = answer_absent_reason(context_answer)
    context_text = _string_value(response, "context-artifact-text")
    if context_reason == "asked-declined":
        record("context.capture", "PASS", "declined")
    elif context_reason:
        record("context.capture", "FAIL", f"data-absent-reason={context_reason}")
    elif context_text is None:
        record("context.capture", "SKIP", "unanswered")
    else:
        record("context.capture", "PASS", f"raw_text_chars={len(context_text)}; no analysis performed")

    sleep_answer = first_answer(response, "sleep-hours")
    sleep_reason = answer_absent_reason(sleep_answer)
    sleep = _quantity_value(response, "sleep-hours")
    if sleep_reason == "asked-declined":
        record("sleep.plausibility", "PASS", "declined")
    elif sleep_reason:
        record("sleep.plausibility", "FAIL", f"data-absent-reason={sleep_reason}")
    elif sleep is None:
        record("sleep.plausibility", "SKIP", "unanswered")
    else:
        record("sleep.plausibility", "PASS" if 0 <= sleep <= 24 else "FAIL", f"hours={sleep}")

    pain_answer = first_answer(response, "pain-score")
    pain_reason = answer_absent_reason(pain_answer)
    pain = _integer_value(response, "pain-score")
    if pain_reason == "asked-declined":
        record("pain.plausibility", "PASS", "declined")
    elif pain_reason:
        record("pain.plausibility", "FAIL", f"data-absent-reason={pain_reason}")
    elif pain is None:
        record("pain.plausibility", "SKIP", "unanswered")
    else:
        record("pain.plausibility", "PASS" if 0 <= pain <= 10 else "FAIL", f"score={pain}")

    heart_answer = first_answer(response, "heart-rate")
    heart_reason = answer_absent_reason(heart_answer)
    heart_rate = _quantity_value(response, "heart-rate")
    if heart_reason == "asked-declined":
        record("heart_rate.plausibility", "PASS", "declined")
    elif heart_reason:
        record("heart_rate.plausibility", "FAIL", f"data-absent-reason={heart_reason}")
    elif heart_rate is None:
        record("heart_rate.plausibility", "SKIP", "unanswered")
    else:
        record(
            "heart_rate.plausibility",
            "PASS" if heart_rate > 0 else "FAIL",
            f"heart_rate={heart_rate} /min",
        )

    phq_codes: list[str | None] = []
    phq_invalid = False
    for link_id in ("phq2-interest", "phq2-depressed"):
        answer = first_answer(response, link_id)
        reason = answer_absent_reason(answer)
        coding = _coding_value(response, link_id)
        code = str(coding.get("code")) if coding and coding.get("code") else None
        if reason and reason != "asked-declined":
            phq_invalid = True
        if code and code not in PHQ_SCORE_BY_CODE:
            phq_invalid = True
        phq_codes.append(code)
    record(
        "phq2.answers",
        "FAIL" if phq_invalid else ("PASS" if any(phq_codes) else "SKIP"),
        f"codes={phq_codes}",
    )

    expected_total = None
    if len(phq_codes) == 2 and all(code in PHQ_SCORE_BY_CODE for code in phq_codes):
        expected_total = sum(PHQ_SCORE_BY_CODE[str(code)] for code in phq_codes)
    total_observation = observation_by_loinc(bundle, PHQ2_TOTAL)
    actual_total = total_observation.get("valueInteger") if total_observation else None
    if expected_total is None:
        record(
            "phq2.total",
            "PASS" if total_observation is None else "FAIL",
            "total omitted unless both component answers are present",
        )
    else:
        record(
            "phq2.total",
            "PASS" if actual_total == expected_total else "FAIL",
            f"expected={expected_total}; actual={actual_total}",
        )

    heart_observation = observation_by_loinc(bundle, HEART_RATE_LOINC)
    if heart_rate is None:
        record(
            "heart_rate.materialization",
            "PASS" if heart_observation is None else "FAIL",
            "no answered heart rate -> no heart-rate Observation",
        )
    else:
        quantity = (heart_observation or {}).get("valueQuantity") or {}
        preserved = (
            heart_observation is not None
            and quantity.get("value") == heart_rate
            and quantity.get("system") == UCUM_SYSTEM
            and quantity.get("code") == "/min"
        )
        record(
            "heart_rate.materialization",
            "PASS" if preserved else "FAIL",
            f"entered={heart_rate}; observation={quantity}",
        )

    pain_observation = observation_by_loinc(bundle, PAIN_LOINC)
    if pain is None:
        record(
            "pain.materialization",
            "PASS" if pain_observation is None else "FAIL",
            "no answered pain -> no pain Observation",
        )
    else:
        preserved = pain_observation is not None and pain_observation.get("valueInteger") == pain
        record(
            "pain.materialization",
            "PASS" if preserved else "FAIL",
            f"entered={pain}; observation={(pain_observation or {}).get('valueInteger')}",
        )

    medication_status = _boolean_value(response, "medication-status")
    medications = bundle_resources(bundle, "MedicationStatement")
    if medication_status is True:
        record(
            "medications.cardinality",
            "PASS" if medications else "FAIL",
            f"status=yes; MedicationStatements={len(medications)}",
        )
    elif medication_status is False:
        record(
            "medications.cardinality",
            "PASS" if not medications else "FAIL",
            f"status=no; MedicationStatements={len(medications)}",
        )
    else:
        record(
            "medications.cardinality",
            "PASS" if not medications else "FAIL",
            f"status=unanswered/declined; MedicationStatements={len(medications)}",
        )

    for index, medication in enumerate(medications, start=1):
        concept = medication.get("medicationCodeableConcept") or {}
        for coding in concept.get("coding", []) or []:
            if not isinstance(coding, Mapping) or not coding.get("code"):
                continue
            record(
                f"medication.{index}.coding",
                "PASS" if coding.get("system") == RXNORM_SYSTEM else "FAIL",
                f"system={coding.get('system')!r}; code={coding.get('code')!r}",
            )

        dosages = medication.get("dosage") or []
        if dosages and isinstance(dosages[0], Mapping):
            dose_and_rate = dosages[0].get("doseAndRate") or []
            if dose_and_rate and isinstance(dose_and_rate[0], Mapping):
                quantity = dose_and_rate[0].get("doseQuantity") or {}
                value = quantity.get("value") if isinstance(quantity, Mapping) else None
                record(
                    f"medication.{index}.dose",
                    "PASS" if isinstance(value, (int, float)) and value >= 0 else "FAIL",
                    f"dose={quantity}",
                )

    failed = [check for check in checks if check["status"] == "FAIL"]
    return {
        "status": "FAIL" if failed else "PASS",
        "scope": "MONARCH_CAPTURE_AND_CAREGIVER_BASELINE",
        "claim": "Monarch capture conformance plus caregiver plausibility and semantic-preservation checks.",
        "checks": checks,
        "structural": structural,
    }
