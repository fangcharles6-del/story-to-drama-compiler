"""Generated-reference Rights Manifest and current-status evidence boundary.

This module implements the isolated, deterministic, zero-authority boundary accepted by
SDC-ADR-044.  It performs no Provider, Runtime, network, credential, persistence, publication,
qualification renewal, asset promotion, or paid-generation operation.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated, ClassVar, Literal, NoReturn, Self, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)

from sdc.generated_reference_candidate import (
    CreativeSampleGeneratedReferenceCandidateQualificationDecisionV1,
    CreativeSampleGeneratedReferenceCandidateQualificationRequestV1,
    CreativeSampleGeneratedReferenceCandidateV1,
    CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1,
    GeneratedReferenceQualificationEvidenceInput,
    GeneratedReferenceQualificationEvidenceReferenceV1,
    creative_sample_generated_reference_candidate_qualification_decision_projection,
    creative_sample_generated_reference_candidate_qualification_decision_sha256,
    creative_sample_generated_reference_candidate_qualification_request_projection,
    creative_sample_generated_reference_candidate_qualification_request_sha256,
    creative_sample_generated_reference_candidate_sha256,
    creative_sample_generated_reference_provider_attempt_outcome_sha256,
)
from sdc.visual_reference_prompt_compiler import (
    CreativeSampleReferenceVisualPromptArtifactV1,
    creative_sample_reference_visual_prompt_artifact_sha256,
)

_MANIFEST_POLICY_JSON = (
    '{"action_time_rule":"DECISION_AT_LE_MAKER_PREPARED_AT_LE_MANIFEST_AT_EQ_CHECKER_REVI'
    'EWED_AT","compiler_gate_basis":[{"basis":"COMPILER_REVALIDATED_EXACT_ADR042_ADR043_C'
    'LOSURE","gate_ordinal":0},{"basis":"COMPILER_REVALIDATED_DISTINCT_ROLE_AND_ACTION_CL'
    'OSURE","gate_ordinal":10}],"evidence_scope":"EXPLICIT_FINITE_BOUND_SET_ONLY","manife'
    'st_gate_evidence_mapping":[{"evidence_category":null,"evidence_ordinal":null,"gate":'
    '"PROVENANCE_AND_CANDIDATE_CLOSURE","gate_ordinal":0,"source":"COMPILER_DERIVED"},{"e'
    'vidence_category":"SUBMISSION_TIME_AUTHORIZATION","evidence_ordinal":0,"gate":"SUBMI'
    'SSION_TIME_AUTHORIZATION","gate_ordinal":1,"source":"HUMAN_REVIEW_EVIDENCE"},{"evide'
    'nce_category":"PROVIDER_TERMS_AT_SUBMISSION","evidence_ordinal":1,"gate":"PROVIDER_T'
    'ERMS_AT_SUBMISSION","gate_ordinal":2,"source":"HUMAN_REVIEW_EVIDENCE"},{"evidence_ca'
    'tegory":"INPUT_TEXT_AND_MEDIA_RIGHTS","evidence_ordinal":2,"gate":"INPUT_TEXT_AND_ME'
    'DIA_RIGHTS","gate_ordinal":3,"source":"HUMAN_REVIEW_EVIDENCE"},{"evidence_category":'
    '"OUTPUT_COPYRIGHT_AND_COMMERCIAL_SCOPE","evidence_ordinal":3,"gate":"OUTPUT_COPYRIGH'
    'T_AND_COMMERCIAL_SCOPE","gate_ordinal":4,"source":"HUMAN_REVIEW_EVIDENCE"},{"evidenc'
    'e_category":"LIKENESS_PRIVACY_AND_SENSITIVE_DATA","evidence_ordinal":4,"gate":"LIKEN'
    'ESS_PRIVACY_AND_SENSITIVE_DATA","gate_ordinal":5,"source":"HUMAN_REVIEW_EVIDENCE"},{'
    '"evidence_category":"BRAND_AND_PROTECTED_CONTENT","evidence_ordinal":5,"gate":"BRAND'
    '_AND_PROTECTED_CONTENT","gate_ordinal":6,"source":"HUMAN_REVIEW_EVIDENCE"},{"evidenc'
    'e_category":"TERRITORY_DURATION_AND_ALLOWED_USE","evidence_ordinal":6,"gate":"TERRIT'
    'ORY_DURATION_AND_ALLOWED_USE","gate_ordinal":7,"source":"HUMAN_REVIEW_EVIDENCE"},{"e'
    'vidence_category":"RETENTION_AND_DELETION_OBLIGATIONS","evidence_ordinal":7,"gate":"'
    'RETENTION_AND_DELETION_OBLIGATIONS","gate_ordinal":8,"source":"HUMAN_REVIEW_EVIDENCE'
    '"},{"evidence_category":"TRAINING_USE_PROHIBITION","evidence_ordinal":8,"gate":"TRAI'
    'NING_USE_PROHIBITION","gate_ordinal":9,"source":"HUMAN_REVIEW_EVIDENCE"},{"evidence_'
    'category":null,"evidence_ordinal":null,"gate":"REVIEWER_ROLE_AND_EVIDENCE_CLOSURE","'
    'gate_ordinal":10,"source":"COMPILER_DERIVED"}],"manifest_max_age_seconds":86400,"man'
    'ifest_outcome":"PASS_FOR_SEPARATE_GENERATED_CURRENT_STATUS_ASSESSMENT","manifest_rev'
    'iew_evidence_category_order":["SUBMISSION_TIME_AUTHORIZATION","PROVIDER_TERMS_AT_SUB'
    'MISSION","INPUT_TEXT_AND_MEDIA_RIGHTS","OUTPUT_COPYRIGHT_AND_COMMERCIAL_SCOPE","LIKE'
    'NESS_PRIVACY_AND_SENSITIVE_DATA","BRAND_AND_PROTECTED_CONTENT","TERRITORY_DURATION_A'
    'ND_ALLOWED_USE","RETENTION_AND_DELETION_OBLIGATIONS","TRAINING_USE_PROHIBITION"],"ma'
    'nifest_review_gate_order":["PROVENANCE_AND_CANDIDATE_CLOSURE","SUBMISSION_TIME_AUTHO'
    'RIZATION","PROVIDER_TERMS_AT_SUBMISSION","INPUT_TEXT_AND_MEDIA_RIGHTS","OUTPUT_COPYR'
    'IGHT_AND_COMMERCIAL_SCOPE","LIKENESS_PRIVACY_AND_SENSITIVE_DATA","BRAND_AND_PROTECTE'
    'D_CONTENT","TERRITORY_DURATION_AND_ALLOWED_USE","RETENTION_AND_DELETION_OBLIGATIONS"'
    ',"TRAINING_USE_PROHIBITION","REVIEWER_ROLE_AND_EVIDENCE_CLOSURE"],"manifest_review_p'
    'ayload_profile":"sdc.generated-reference-rights-manifest-review-payload.v1","manifes'
    't_scope":"GENERATED_REFERENCE_RIGHTS_REVIEW_ONLY","manifest_valid_until_rule":"MIN_M'
    'ANIFEST_AT_PLUS_86400_CURRENT_EVIDENCE_AND_REVIEWED_SCOPE_END","policy_id":"sdc.gene'
    'rated-reference-rights-manifest-policy","policy_version":"1.0.0","qualification_requ'
    'ired_decision":"PASS_FOR_SEPARATE_GENERATED_RIGHTS_MANIFEST_REVIEW","qualification_s'
    'cope":"GENERATED_REFERENCE_CANDIDATE_INTAKE_ONLY","required_gate_result":"PASS","res'
    'ource_limits":{"allowed_use_codes_max":32,"basis_code_points_max":1000,"generic_cont'
    'ainer_items_max":64,"identity_reference_document_bytes_max":16384,"json_depth_max":3'
    '2,"manifest_document_bytes_max":262144,"manifest_review_payload_bytes_max":262144,"r'
    'etained_action_document_bytes_max":262144,"review_evidence_document_bytes_max":26214'
    '4,"territory_codes_max":64,"top_level_object_members_max":128},"review_action_projec'
    'tion_rule":"PAYLOAD_THEN_MAKER_THEN_CHECKER_NO_FINAL_MANIFEST_SHA","reviewed_scope_b'
    'asis_gate_mapping":[{"field":"output_copyright_and_commercial_scope_basis","gate_ord'
    'inal":4},{"field":"likeness_privacy_and_sensitive_data_basis","gate_ordinal":5},{"fi'
    'eld":"brand_and_protected_content_basis","gate_ordinal":6},{"field":"retention_and_d'
    'eletion_basis","gate_ordinal":8},{"field":"training_use_prohibition_basis","gate_ord'
    'inal":9}],"reviewer_rule":"MANIFEST_MAKER_DISTINCT_FROM_CHECKER_AND_CHECKER_DISTINCT'
    '_FROM_QUALIFIER","scope_code_order":"STRICT_ASCENDING_UTF8_BYTES_UNIQUE","scope_rule'
    '":"CHECKER_REVIEWED_SCOPE_SUBSET_OF_MAKER_PROPOSED_SCOPE","time_rule":"DECISION_AT_L'
    'E_MANIFEST_AT_LT_QUALIFICATION_VALID_UNTIL","zero_authority":true}'
)
_CURRENT_STATUS_POLICY_JSON = (
    '{"adverse_category_order":["HOLD_ACTIVE","REVOCATION_EFFECTIVE","COMPLAINT_OPEN","DI'
    'SPUTE_OPEN"],"basis_claim_matrix":[{"absent_basis_codes":["HOLD_RELEASED"],"category'
    '":"HOLD_ACTIVE","present_basis_codes":["HOLD_IMPOSED"]},{"absent_basis_codes":["RIGH'
    'TS_REINSTATED"],"category":"REVOCATION_EFFECTIVE","present_basis_codes":["REVOCATION'
    '_ISSUED","SUPERSEDED","RETENTION_DELETION_VIOLATION_CONFIRMED","TRAINING_VIOLATION_C'
    'ONFIRMED"]},{"absent_basis_codes":["COMPLAINT_RESOLVED"],"category":"COMPLAINT_OPEN"'
    ',"present_basis_codes":["COMPLAINT_RECEIVED"]},{"absent_basis_codes":["DISPUTE_RESOL'
    'VED"],"category":"DISPUTE_OPEN","present_basis_codes":["DISPUTE_OPENED"]},{"absent_b'
    'asis_codes":["RIGHTS_EXPIRED_TERMINATED_OR_SUSPENDED"],"category":"RIGHTS_BASIS_CURR'
    'ENT","present_basis_codes":["RIGHTS_CONFIRMED"]},{"absent_basis_codes":["IDENTITY_EX'
    'PIRED_REVOKED_OR_SUPERSEDED"],"category":"IDENTITY_BINDING_CURRENT","present_basis_c'
    'odes":["IDENTITY_CONFIRMED"]},{"absent_basis_codes":["TERMS_CHANGED_OR_INCOMPATIBLE"'
    '],"category":"PROVIDER_TERMS_COMPATIBILITY_CURRENT","present_basis_codes":["TERMS_CO'
    'MPATIBLE"]},{"absent_basis_codes":["RETENTION_DELETION_UNRESOLVED_OR_NONCOMPLIANT"],'
    '"category":"RETENTION_DELETION_COMPLIANCE_CURRENT","present_basis_codes":["RETENTION'
    '_DELETION_COMPLIANT"]},{"absent_basis_codes":["TRAINING_UNRESOLVED_OR_VIOLATED"],"ca'
    'tegory":"TRAINING_USE_PROHIBITION_CURRENT","present_basis_codes":["TRAINING_PROHIBIT'
    'ION_CONFIRMED"]}],"category_effect_rules":{"ADVERSE_ABSENT_WITH_EVIDENCE":"ADVERSE_A'
    'BSENT","ADVERSE_PRESENT":"ADVERSE_PRESENT","ANY_CONFLICT_NOT_ASSESSED_OR_UNKNOWN":"I'
    'NDETERMINATE","POSITIVE_ABSENT_WITH_EVIDENCE":"POSITIVE_ABSENT","POSITIVE_PRESENT":"'
    'POSITIVE_PRESENT"},"category_reduction_rules":["NO_USABLE_TARGET_YIELDS_NOT_ASSESSED'
    '","ONE_DISTINCT_USABLE_CLAIM_WITHOUT_FORK_YIELDS_THAT_CLAIM","MULTIPLE_DISTINCT_USAB'
    'LE_CLAIMS_YIELD_CONFLICT","INCOMPARABLE_USABLE_HEADS_WITHOUT_SUPPLIED_RECONCILIATION'
    '_DESCENDANT_YIELD_CONFLICT_EVEN_IF_CLAIMS_MATCH"],"category_result_reference_members'
    'hip":{"category_observation_refs":"EVERY_AND_ONLY_REQUEST_TARGET_FOR_CATEGORY","reli'
    'ed_on_observation_refs":"EVERY_AND_ONLY_CATEGORY_TARGET_WITH_COMPLETE_CHAIN_CLAIM_NO'
    'T_NOT_ASSESSED_AND_MAX_OBSERVED_AT_VALID_FROM_LE_EVALUATED_AT_LT_VALID_UNTIL"},"cate'
    'gory_result_valid_until_rule":"MIN_REQUEST_VALID_UNTIL_MANIFEST_VALID_UNTIL_AND_RELI'
    'ED_TARGET_VALID_UNTIL","chain_scope_fields":["subject_closure_id","subject_closure_s'
    'ha256","category","source_identity_ref_sha256","source_kind","observation_profile","'
    'policy_version"],"claim_values":["PRESENT","ABSENT_WITH_EVIDENCE","UNKNOWN","NOT_ASS'
    'ESSED","CONFLICT"],"coverage_byte_accounting":"COUNT_EVERY_OCCURRENCE_BEFORE_UNIQUEN'
    'ESS","current_requirements":"ALL_ADVERSE_ABSENT_WITH_EVIDENCE_AND_ALL_POSITIVE_PRESE'
    'NT","decision_category_tuple_membership":{"final_status_precedence_rule":"RETAIN_ALL'
    '_MATCHING_MEMBERS_NEVER_CLEAR_DIAGNOSTIC_TUPLES","held_categories":[{"category":"HOL'
    'D_ACTIVE","deterministic_effect":"ADVERSE_PRESENT"},{"category":"COMPLAINT_OPEN","de'
    'terministic_effect":"ADVERSE_PRESENT"},{"category":"DISPUTE_OPEN","deterministic_eff'
    'ect":"ADVERSE_PRESENT"},{"category":"RIGHTS_BASIS_CURRENT","deterministic_effect":"P'
    'OSITIVE_ABSENT"},{"category":"IDENTITY_BINDING_CURRENT","deterministic_effect":"POSI'
    'TIVE_ABSENT"},{"category":"PROVIDER_TERMS_COMPATIBILITY_CURRENT","deterministic_effe'
    'ct":"POSITIVE_ABSENT"},{"category":"RETENTION_DELETION_COMPLIANCE_CURRENT","determin'
    'istic_effect":"POSITIVE_ABSENT"},{"category":"TRAINING_USE_PROHIBITION_CURRENT","det'
    'erministic_effect":"POSITIVE_ABSENT"}],"indeterminate_categories":[{"category":"HOLD'
    '_ACTIVE","deterministic_effect":"INDETERMINATE"},{"category":"REVOCATION_EFFECTIVE",'
    '"deterministic_effect":"INDETERMINATE"},{"category":"COMPLAINT_OPEN","deterministic_'
    'effect":"INDETERMINATE"},{"category":"DISPUTE_OPEN","deterministic_effect":"INDETERM'
    'INATE"},{"category":"RIGHTS_BASIS_CURRENT","deterministic_effect":"INDETERMINATE"},{'
    '"category":"IDENTITY_BINDING_CURRENT","deterministic_effect":"INDETERMINATE"},{"cate'
    'gory":"PROVIDER_TERMS_COMPATIBILITY_CURRENT","deterministic_effect":"INDETERMINATE"}'
    ',{"category":"RETENTION_DELETION_COMPLIANCE_CURRENT","deterministic_effect":"INDETER'
    'MINATE"},{"category":"TRAINING_USE_PROHIBITION_CURRENT","deterministic_effect":"INDE'
    'TERMINATE"}],"revoked_categories":[{"category":"REVOCATION_EFFECTIVE","deterministic'
    '_effect":"ADVERSE_PRESENT"}]},"error_orders":{"as_of":["AS_OF_CONTRACT_INVALID","REC'
    'ORD_JOINT_REPLAY_FAILED","AS_OF_PRECEDES_RECORD_EVALUATION","INTERNAL_RESULT_INCONSI'
    'STENCY"],"chain_replay":["COUNT_OUT_OF_RANGE","OBSERVATION_CONTRACT_INVALID","DUPLIC'
    'ATE_OBSERVATION_ID","DUPLICATE_OBSERVATION_DOCUMENT_SHA256","DUPLICATE_OBSERVATION_C'
    'HAIN_SHA256","CHAIN_SCOPE_MISMATCH","ORPHAN_REFERENCE","REFERENCE_ANCHOR_MISMATCH","'
    'IMMEDIATE_LINK_INVALID","CYCLE_DETECTED","GENESIS_COUNT_INVALID","DISCONNECTED_GRAPH'
    '","RECONCILIATION_HEAD_ANCESTRY_CONFLICT","INTERNAL_RESULT_INCONSISTENCY"],"coverage'
    '":["CHAIN_COLLECTION_CONTRACT_INVALID","CHAIN_COUNT_OUT_OF_RANGE","CHAIN_INPUT_CONTR'
    'ACT_INVALID","TARGET_COUNT_OUT_OF_RANGE","OBSERVATION_COUNT_OUT_OF_RANGE","AGGREGATE'
    '_CANONICAL_BYTES_OUT_OF_RANGE","EVIDENCE_RECORD_INVALID","REQUEST_TARGET_COVERED_MUL'
    'TIPLE_TIMES","REQUEST_TARGET_ANCHOR_MISMATCH","REQUEST_TARGET_NOT_IN_RECORD","REQUES'
    'T_OBSERVATION_NOT_COVERED","CHAIN_REPLAY_FAILED","DUPLICATE_LOGICAL_CHAIN","CROSS_CH'
    'AIN_DUPLICATE_OBSERVATION_ID","CROSS_CHAIN_DUPLICATE_OBSERVATION_DOCUMENT_SHA256","C'
    'ROSS_CHAIN_DUPLICATE_OBSERVATION_CHAIN_SHA256","CROSS_CHAIN_DUPLICATE_OBSERVATION_SE'
    'T_SHA256","REQUEST_TARGET_NOT_RESOLVED_IN_CHAIN","CHAIN_TARGET_SET_MISMATCH","UNRELA'
    'TED_SUPPORT_OBSERVATION","RECORD_REBUILD_MISMATCH","INTERNAL_RESULT_INCONSISTENCY"],'
    '"joint_replay":["RECORD_CHAIN_COVERAGE_REPLAY_FAILED","TARGET_OBSERVATION_DERIVATION'
    '_INCONSISTENT","PROVIDED_OBJECT_CLOSURE_REPLAY_FAILED","INTERNAL_RESULT_INCONSISTENC'
    'Y"],"receipt":["RECEIPT_CONTRACT_INVALID","AS_OF_ASSESSMENT_REPLAY_FAILED","ASSESSME'
    'NT_RESULT_INCONSISTENT","INTERNAL_RECEIPT_INCONSISTENCY","RECEIPT_REPLAY_MISMATCH"]}'
    ',"evidence_scope":"EXPLICIT_FINITE_BOUND_SET_ONLY","generic_basis_order":["INITIAL_S'
    'TATUS_UNKNOWN","INITIAL_STATUS_NOT_ASSESSED","STATUS_RECONFIRMED","STATUS_BECAME_UNK'
    'NOWN","CONFLICT_IDENTIFIED","CONFLICT_RECONCILED"],"generic_basis_source_kind_rule":'
    '"INITIAL_UNKNOWN_INITIAL_NOT_ASSESSED_STATUS_BECAME_UNKNOWN_AND_CONFLICT_IDENTIFIED_'
    "USE_CATEGORY_APPLICABLE_KIND_STATUS_RECONFIRMED_AND_CONFLICT_RECONCILED_REUSE_CHAIN_"
    'SCOPE_KIND","limitation_codes":["SOURCE_AUTHENTICITY_NOT_PROVEN","SOURCE_COMPLETENES'
    'S_NOT_PROVEN","CHAIN_COMPLETENESS_NOT_PROVEN","REALITY_CURRENTNESS_NOT_PROVEN","SCOP'
    'E_LIMITED_TO_DECLARED_SUBJECT","TIME_WINDOW_LIMITED","LEGAL_EFFECT_NOT_DETERMINED"],'
    '"limitation_rule":"EXACT_POLICY_ORDER_NO_OMISSION_EXTENSION_OR_REORDERING","max_wind'
    'ow_seconds":86400,"observation_profile":"sdc.generated-reference-current-status-obse'
    'rvation-profile.v1","ordering_rules":{"category_observation_refs":"REQUEST_ORDER_FIL'
    'TERED_BY_CATEGORY","category_results":"EXACT_FULL_CATEGORY_ORDER","decision_derived_'
    'category_tuples":"STABLE_SUBSEQUENCE_OF_FULL_CATEGORY_ORDER_FILTERED_BY_EFFECT","exp'
    'licit_chain_set_chain_inputs":"STRICT_ASCENDING_CHAIN_SCOPE_SHA256_THEN_GENESIS_OBSE'
    'RVATION_ID","full_category_order":["HOLD_ACTIVE","REVOCATION_EFFECTIVE","COMPLAINT_O'
    'PEN","DISPUTE_OPEN","RIGHTS_BASIS_CURRENT","IDENTITY_BINDING_CURRENT","PROVIDER_TERM'
    'S_COMPATIBILITY_CURRENT","RETENTION_DELETION_COMPLIANCE_CURRENT","TRAINING_USE_PROHI'
    'BITION_CURRENT"],"logical_chain_key_fields":["chain_scope_sha256","genesis_observati'
    'on_id"],"logical_chain_uniqueness":"EQUAL_KEYS_FAIL_SAME_SCOPE_DIFFERENT_GENESIS_IS_'
    'DISTINCT","observation_set_observation_occurrences":"STRICT_ASCENDING_OBSERVATION_ID'
    '","observation_set_target_observation_refs":"STABLE_SUBSEQUENCE_OF_REQUEST_OBSERVATI'
    'ON_REFS_FILTERED_BY_LOGICAL_CHAIN","reconciliation_predecessor_heads":"STRICT_ASCEND'
    'ING_OBSERVATION_ID_OBSERVATION_SHA256_CHAIN_SHA256","relied_on_observation_refs":"ST'
    'ABLE_SUBSEQUENCE_OF_CATEGORY_OBSERVATION_REFS","request_observation_refs":"STRICT_AS'
    'CENDING_FULL_CATEGORY_ORDER_THEN_VALID_FROM_THEN_OBSERVATION_ID","target_coverage":"'
    'REQUEST_ORDER"},"policy_id":"sdc.generated-reference-current-status-policy","policy_'
    'version":"1.0.0","positive_category_order":["RIGHTS_BASIS_CURRENT","IDENTITY_BINDING'
    '_CURRENT","PROVIDER_TERMS_COMPATIBILITY_CURRENT","RETENTION_DELETION_COMPLIANCE_CURR'
    'ENT","TRAINING_USE_PROHIBITION_CURRENT"],"precedence":["EXPIRED","REVOKED","HELD","I'
    'NDETERMINATE","CURRENT"],"request_reference_rule":"EXPLICIT_TARGET_OBSERVATIONS_ANCE'
    'STOR_TARGETS_ALLOWED_NO_TERMINAL_INFERENCE","resolution_rules":{"CURRENT":"ALL_ADVER'
    'SE_ABSENT_WITH_EVIDENCE_AND_ALL_POSITIVE_PRESENT","EXPIRED":"AS_OF_GE_STATUS_VALID_U'
    'NTIL_OR_MANIFEST_VALID_UNTIL","HELD":"HOLD_COMPLAINT_OR_DISPUTE_PRESENT_OR_ANY_POSIT'
    'IVE_ABSENT_WITH_EVIDENCE","INDETERMINATE":"COMPLETE_STRUCTURE_WITH_UNKNOWN_NOT_ASSES'
    'SED_CONFLICT_OR_NO_USABLE_EVIDENCE","REVOKED":"REVOCATION_EFFECTIVE_PRESENT"},"resou'
    'rce_limits":{"aggregate_observation_occurrence_bytes_max":16777216,"as_of_receipt_do'
    'cument_bytes_max":65536,"basis_code_points_max":1000,"chain_inputs_max":32,"chain_in'
    'puts_min":1,"generic_container_items_max":64,"identity_reference_document_bytes_max"'
    ':16384,"json_depth_max":32,"observations_per_chain_max":64,"observations_per_chain_m'
    'in":1,"reconciliation_heads_max":8,"request_instruction_decision_record_bytes_max":2'
    '097152,"request_targets_max":32,"request_targets_min":9,"retained_action_document_by'
    'tes_max":262144,"retained_source_object_bytes_max":262144,"source_observation_docume'
    'nt_bytes_max":262144,"source_reference_document_bytes_max":16384,"targets_per_chain_'
    'max":32,"targets_per_chain_min":1,"top_level_object_members_max":128},"result_values'
    '":["EXPIRED","REVOKED","HELD","INDETERMINATE","CURRENT"],"reviewer_rule":"STATUS_PRE'
    'PARER_DISTINCT_FROM_STATUS_CHECKER","source_kind_applicability":[{"basis_codes":["HO'
    'LD_IMPOSED","HOLD_RELEASED"],"category":"HOLD_ACTIVE","source_kinds":["INTERNAL_HOLD'
    '_RECORD"]},{"basis_codes":["REVOCATION_ISSUED","RIGHTS_REINSTATED","SUPERSEDED"],"ca'
    'tegory":"REVOCATION_EFFECTIVE","source_kinds":["REVOCATION_NOTICE"]},{"basis_codes":'
    '["RETENTION_DELETION_VIOLATION_CONFIRMED"],"category":"REVOCATION_EFFECTIVE","source'
    '_kinds":["RETENTION_DELETION_RECORD"]},{"basis_codes":["TRAINING_VIOLATION_CONFIRMED'
    '"],"category":"REVOCATION_EFFECTIVE","source_kinds":["TRAINING_USE_RECORD"]},{"basis'
    '_codes":["COMPLAINT_RECEIVED","COMPLAINT_RESOLVED"],"category":"COMPLAINT_OPEN","sou'
    'rce_kinds":["COMPLAINT_RECORD"]},{"basis_codes":["DISPUTE_OPENED","DISPUTE_RESOLVED"'
    '],"category":"DISPUTE_OPEN","source_kinds":["DISPUTE_RECORD"]},{"basis_codes":["RIGH'
    'TS_CONFIRMED","RIGHTS_EXPIRED_TERMINATED_OR_SUSPENDED"],"category":"RIGHTS_BASIS_CUR'
    'RENT","source_kinds":["RIGHTS_HOLDER_DECLARATION","LICENSOR_DECLARATION"]},{"basis_c'
    'odes":["IDENTITY_CONFIRMED","IDENTITY_EXPIRED_REVOKED_OR_SUPERSEDED"],"category":"ID'
    'ENTITY_BINDING_CURRENT","source_kinds":["IDENTITY_BINDING_RECORD"]},{"basis_codes":['
    '"TERMS_COMPATIBLE","TERMS_CHANGED_OR_INCOMPATIBLE"],"category":"PROVIDER_TERMS_COMPA'
    'TIBILITY_CURRENT","source_kinds":["PROVIDER_TERMS_RECORD"]},{"basis_codes":["RETENTI'
    'ON_DELETION_COMPLIANT","RETENTION_DELETION_UNRESOLVED_OR_NONCOMPLIANT"],"category":"'
    'RETENTION_DELETION_COMPLIANCE_CURRENT","source_kinds":["RETENTION_DELETION_RECORD"]}'
    ',{"basis_codes":["TRAINING_PROHIBITION_CONFIRMED","TRAINING_UNRESOLVED_OR_VIOLATED"]'
    ',"category":"TRAINING_USE_PROHIBITION_CURRENT","source_kinds":["TRAINING_USE_RECORD"'
    ']}],"source_kind_order":["RIGHTS_HOLDER_DECLARATION","LICENSOR_DECLARATION","PROVIDE'
    'R_TERMS_RECORD","INTERNAL_HOLD_RECORD","REVOCATION_NOTICE","COMPLAINT_RECORD","DISPU'
    'TE_RECORD","IDENTITY_BINDING_RECORD","RETENTION_DELETION_RECORD","TRAINING_USE_RECOR'
    'D"],"status_action_projection_rule":"PREPARER_ACTION_THEN_REQUEST_THEN_CHECKER_ACTIO'
    'N_THEN_INSTRUCTION_THEN_DECISION","status_subject":"EXACT_GENERATED_RIGHTS_MANIFEST_'
    'CLOSURE","status_valid_until_rule":"MIN_OF_NINE_CATEGORY_RESULT_VALID_UNTIL_VALUES",'
    '"structural_failure_rule":"MALFORMED_OR_MISSING_REFERENCED_CLOSURE_FAILS_WITHOUT_RES'
    'ULT","subject_closure_profile":"sdc.generated-reference-current-status-subject-closu'
    're.v1","successful_conflict_rule":"COMPLETE_UNRECONCILED_MULTI_HEAD_CHAIN_YIELDS_CON'
    'FLICT","transition_matrix":{"GENESIS":[{"basis":"CATEGORY_SPECIFIC_PRESENT","to":"PR'
    'ESENT"},{"basis":"CATEGORY_SPECIFIC_ABSENT","to":"ABSENT_WITH_EVIDENCE"},{"basis":"I'
    'NITIAL_STATUS_UNKNOWN","to":"UNKNOWN"},{"basis":"INITIAL_STATUS_NOT_ASSESSED","to":"'
    'NOT_ASSESSED"},{"basis":"CONFLICT_IDENTIFIED","to":"CONFLICT"}],"RECONCILIATION_2_TO'
    '_8_HEADS":[{"basis":"CONFLICT_RECONCILED","final_claims":["PRESENT","ABSENT_WITH_EVI'
    'DENCE","UNKNOWN"]},{"basis":"CONFLICT_IDENTIFIED","final_claims":["CONFLICT"]},{"fin'
    'al_claims":["NOT_ASSESSED"],"result":"REJECT"}],"SUCCESSOR":[{"basis":"INITIAL_STATU'
    'S_UNKNOWN","from_claims":["NOT_ASSESSED"],"to":"UNKNOWN"},{"basis":"CATEGORY_SPECIFI'
    'C_PRESENT","from_claims":["NOT_ASSESSED","UNKNOWN"],"to":"PRESENT"},{"basis":"CATEGO'
    'RY_SPECIFIC_ABSENT","from_claims":["NOT_ASSESSED","UNKNOWN"],"to":"ABSENT_WITH_EVIDE'
    'NCE"},{"basis":"STATUS_RECONFIRMED","from_claims":["PRESENT"],"to":"PRESENT"},{"basi'
    's":"STATUS_RECONFIRMED","from_claims":["ABSENT_WITH_EVIDENCE"],"to":"ABSENT_WITH_EVI'
    'DENCE"},{"basis":"CATEGORY_SPECIFIC_ABSENT","from_claims":["PRESENT"],"to":"ABSENT_W'
    'ITH_EVIDENCE"},{"basis":"CATEGORY_SPECIFIC_PRESENT","from_claims":["ABSENT_WITH_EVID'
    'ENCE"],"to":"PRESENT"},{"basis":"STATUS_BECAME_UNKNOWN","from_claims":["PRESENT","AB'
    'SENT_WITH_EVIDENCE"],"to":"UNKNOWN"},{"basis":"CONFLICT_IDENTIFIED","from_claims":["'
    'NOT_ASSESSED","UNKNOWN","PRESENT","ABSENT_WITH_EVIDENCE"],"to":"CONFLICT"}],"SUCCESS'
    'OR_REJECTION":[{"from_claims":["UNKNOWN"],"result":"REJECT","to_claims":["UNKNOWN"]}'
    ',{"from_claims":["NOT_ASSESSED","UNKNOWN","PRESENT","ABSENT_WITH_EVIDENCE","CONFLICT'
    '"],"result":"REJECT","to_claims":["NOT_ASSESSED"]},{"from_claims":["CONFLICT"],"resu'
    'lt":"REJECT","to_claims":["PRESENT","ABSENT_WITH_EVIDENCE","UNKNOWN","NOT_ASSESSED",'
    '"CONFLICT"]}]},"window_semantics":"EVALUATED_AT_INCLUSIVE_STATUS_VALID_UNTIL_EXCLUSI'
    'VE","zero_authority":true}'
)

GENERATED_REFERENCE_RIGHTS_MANIFEST_POLICY_ID = "sdc.generated-reference-rights-manifest-policy"
GENERATED_REFERENCE_RIGHTS_MANIFEST_POLICY_VERSION = "1.0.0"
GENERATED_REFERENCE_RIGHTS_MANIFEST_POLICY_DOCUMENT_SHA256 = (
    "7d9f72f134b5be5f68bb55f25ee898736bd84d39b2ff6917e0e2ecab447f8f16"
)
GENERATED_REFERENCE_CURRENT_STATUS_POLICY_ID = "sdc.generated-reference-current-status-policy"
GENERATED_REFERENCE_CURRENT_STATUS_POLICY_VERSION = "1.0.0"
GENERATED_REFERENCE_CURRENT_STATUS_POLICY_DOCUMENT_SHA256 = (
    "cf596012ca0d3bf88d1e49d0aea11184428d047d0e919822032da51f792d61e0"
)

GENERATED_REFERENCE_RIGHTS_MANIFEST_REVIEW_PAYLOAD_SHA256_DOMAIN = (
    b"sdc:generated-reference-rights-manifest-review-payload:v1\0"
)
GENERATED_REFERENCE_RIGHTS_MANIFEST_SHA256_DOMAIN = b"sdc:generated-reference-rights-manifest:v1\0"
GENERATED_REFERENCE_CURRENT_STATUS_SUBJECT_CLOSURE_SHA256_DOMAIN = (
    b"sdc:generated-reference-current-status-subject-closure:v1\0"
)
GENERATED_REFERENCE_CURRENT_STATUS_SOURCE_OBSERVATION_SHA256_DOMAIN = (
    b"sdc:generated-reference-current-status-source-observation:v1\0"
)
GENERATED_REFERENCE_CURRENT_STATUS_CHAIN_SCOPE_SHA256_DOMAIN = (
    b"sdc:generated-reference-current-status-chain-scope:v1\0"
)
GENERATED_REFERENCE_CURRENT_STATUS_CHAIN_SHA256_DOMAIN = (
    b"sdc:generated-reference-current-status-chain:v1\0"
)
GENERATED_REFERENCE_CURRENT_STATUS_OBSERVATION_SET_SHA256_DOMAIN = (
    b"sdc:generated-reference-current-status-observation-set:v1\0"
)
GENERATED_REFERENCE_CURRENT_STATUS_REQUEST_SHA256_DOMAIN = (
    b"sdc:generated-reference-current-status-request:v1\0"
)
GENERATED_REFERENCE_CURRENT_STATUS_INSTRUCTION_SHA256_DOMAIN = (
    b"sdc:generated-reference-current-status-instruction:v1\0"
)
GENERATED_REFERENCE_CURRENT_STATUS_DECISION_SHA256_DOMAIN = (
    b"sdc:generated-reference-current-status-decision:v1\0"
)
GENERATED_REFERENCE_CURRENT_STATUS_EVIDENCE_RECORD_SHA256_DOMAIN = (
    b"sdc:generated-reference-current-status-evidence-record:v1\0"
)
GENERATED_REFERENCE_CURRENT_STATUS_EXPLICIT_CHAIN_SET_SHA256_DOMAIN = (
    b"sdc:generated-reference-current-status-explicit-chain-set:v1\0"
)
GENERATED_REFERENCE_CURRENT_STATUS_COVERAGE_SET_SHA256_DOMAIN = (
    b"sdc:generated-reference-current-status-coverage-set:v1\0"
)
GENERATED_REFERENCE_CURRENT_STATUS_JOINT_REPLAY_SHA256_DOMAIN = (
    b"sdc:generated-reference-current-status-joint-replay:v1\0"
)
GENERATED_REFERENCE_CURRENT_STATUS_RECORD_AS_OF_ASSESSMENT_SHA256_DOMAIN = (
    b"sdc:generated-reference-current-status-record-as-of-assessment:v1\0"
)
GENERATED_REFERENCE_CURRENT_STATUS_RECORD_AS_OF_ASSESSMENT_PROVENANCE_SHA256_DOMAIN = (
    b"sdc:generated-reference-current-status-record-as-of-assessment-provenance:v1\0"
)
GENERATED_REFERENCE_CURRENT_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_SHA256_DOMAIN = (
    b"sdc:generated-reference-current-status-record-as-of-assessment-receipt:v1\0"
)

_SCHEMA_VERSION = "1.0.0"
_MAX_JSON_DEPTH = 32
_MAX_CONTAINER_ITEMS = 64
_MAX_FORMAL_ROOT_ITEMS = 128
_MAX_FORMAL_DOCUMENT_BYTES = 2_097_152
_PORTABLE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"
_PORTABLE_CODE_PATTERN = r"^[A-Z][A-Z0-9_]{0,255}$"
_LOWER_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_SEMANTIC_VERSION_PATTERN = r"^(0|[1-9][0-9]{0,9})\.(0|[1-9][0-9]{0,9})\.(0|[1-9][0-9]{0,9})$"
_UTC_SECONDS_PATTERN = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
_MEDIA_TYPE_PATTERN = r"^[a-z0-9][a-z0-9!#$&^_.+-]{0,63}/[a-z0-9][a-z0-9!#$&^_.+-]{0,63}$"

PortableId = Annotated[str, Field(pattern=_PORTABLE_ID_PATTERN)]
PortableCode = Annotated[str, Field(pattern=_PORTABLE_CODE_PATTERN)]
LowerSha256 = Annotated[str, Field(pattern=_LOWER_SHA256_PATTERN)]
SemanticVersion = Annotated[str, Field(pattern=_SEMANTIC_VERSION_PATTERN)]
HumanBasis = Annotated[str, Field(min_length=1, max_length=1000)]

AssetPurpose = Literal["CHARACTER_REFERENCE_ASSET", "SCENE_REFERENCE_ASSET"]
ManifestEvidenceCategory = Literal[
    "SUBMISSION_TIME_AUTHORIZATION",
    "PROVIDER_TERMS_AT_SUBMISSION",
    "INPUT_TEXT_AND_MEDIA_RIGHTS",
    "OUTPUT_COPYRIGHT_AND_COMMERCIAL_SCOPE",
    "LIKENESS_PRIVACY_AND_SENSITIVE_DATA",
    "BRAND_AND_PROTECTED_CONTENT",
    "TERRITORY_DURATION_AND_ALLOWED_USE",
    "RETENTION_AND_DELETION_OBLIGATIONS",
    "TRAINING_USE_PROHIBITION",
]
ManifestReviewGate = Literal[
    "PROVENANCE_AND_CANDIDATE_CLOSURE",
    "SUBMISSION_TIME_AUTHORIZATION",
    "PROVIDER_TERMS_AT_SUBMISSION",
    "INPUT_TEXT_AND_MEDIA_RIGHTS",
    "OUTPUT_COPYRIGHT_AND_COMMERCIAL_SCOPE",
    "LIKENESS_PRIVACY_AND_SENSITIVE_DATA",
    "BRAND_AND_PROTECTED_CONTENT",
    "TERRITORY_DURATION_AND_ALLOWED_USE",
    "RETENTION_AND_DELETION_OBLIGATIONS",
    "TRAINING_USE_PROHIBITION",
    "REVIEWER_ROLE_AND_EVIDENCE_CLOSURE",
]
ManifestGateResult = Literal["PASS", "FAIL", "INDETERMINATE"]
CurrentStatusCategory = Literal[
    "HOLD_ACTIVE",
    "REVOCATION_EFFECTIVE",
    "COMPLAINT_OPEN",
    "DISPUTE_OPEN",
    "RIGHTS_BASIS_CURRENT",
    "IDENTITY_BINDING_CURRENT",
    "PROVIDER_TERMS_COMPATIBILITY_CURRENT",
    "RETENTION_DELETION_COMPLIANCE_CURRENT",
    "TRAINING_USE_PROHIBITION_CURRENT",
]
CurrentStatusClaimValue = Literal[
    "PRESENT", "ABSENT_WITH_EVIDENCE", "UNKNOWN", "NOT_ASSESSED", "CONFLICT"
]
CurrentStatusDeterministicEffect = Literal[
    "ADVERSE_PRESENT",
    "ADVERSE_ABSENT",
    "POSITIVE_PRESENT",
    "POSITIVE_ABSENT",
    "INDETERMINATE",
]
CurrentStatusResult = Literal["EXPIRED", "REVOKED", "HELD", "INDETERMINATE", "CURRENT"]
CurrentStatusSourceKind = Literal[
    "RIGHTS_HOLDER_DECLARATION",
    "LICENSOR_DECLARATION",
    "PROVIDER_TERMS_RECORD",
    "INTERNAL_HOLD_RECORD",
    "REVOCATION_NOTICE",
    "COMPLAINT_RECORD",
    "DISPUTE_RECORD",
    "IDENTITY_BINDING_RECORD",
    "RETENTION_DELETION_RECORD",
    "TRAINING_USE_RECORD",
]
CurrentStatusLinkKind = Literal["GENESIS", "SUCCESSOR", "RECONCILIATION"]
CurrentStatusBasisCode = Literal[
    "HOLD_IMPOSED",
    "HOLD_RELEASED",
    "REVOCATION_ISSUED",
    "RIGHTS_REINSTATED",
    "SUPERSEDED",
    "RETENTION_DELETION_VIOLATION_CONFIRMED",
    "TRAINING_VIOLATION_CONFIRMED",
    "COMPLAINT_RECEIVED",
    "COMPLAINT_RESOLVED",
    "DISPUTE_OPENED",
    "DISPUTE_RESOLVED",
    "RIGHTS_CONFIRMED",
    "RIGHTS_EXPIRED_TERMINATED_OR_SUSPENDED",
    "IDENTITY_CONFIRMED",
    "IDENTITY_EXPIRED_REVOKED_OR_SUPERSEDED",
    "TERMS_COMPATIBLE",
    "TERMS_CHANGED_OR_INCOMPATIBLE",
    "RETENTION_DELETION_COMPLIANT",
    "RETENTION_DELETION_UNRESOLVED_OR_NONCOMPLIANT",
    "TRAINING_PROHIBITION_CONFIRMED",
    "TRAINING_UNRESOLVED_OR_VIOLATED",
    "INITIAL_STATUS_UNKNOWN",
    "INITIAL_STATUS_NOT_ASSESSED",
    "STATUS_RECONFIRMED",
    "STATUS_BECAME_UNKNOWN",
    "CONFLICT_IDENTIFIED",
    "CONFLICT_RECONCILED",
]
CurrentStatusLimitationCode = Literal[
    "SOURCE_AUTHENTICITY_NOT_PROVEN",
    "SOURCE_COMPLETENESS_NOT_PROVEN",
    "CHAIN_COMPLETENESS_NOT_PROVEN",
    "REALITY_CURRENTNESS_NOT_PROVEN",
    "SCOPE_LIMITED_TO_DECLARED_SUBJECT",
    "TIME_WINDOW_LIMITED",
    "LEGAL_EFFECT_NOT_DETERMINED",
]

MANIFEST_REVIEW_EVIDENCE_CATEGORY_ORDER: tuple[ManifestEvidenceCategory, ...] = (
    "SUBMISSION_TIME_AUTHORIZATION",
    "PROVIDER_TERMS_AT_SUBMISSION",
    "INPUT_TEXT_AND_MEDIA_RIGHTS",
    "OUTPUT_COPYRIGHT_AND_COMMERCIAL_SCOPE",
    "LIKENESS_PRIVACY_AND_SENSITIVE_DATA",
    "BRAND_AND_PROTECTED_CONTENT",
    "TERRITORY_DURATION_AND_ALLOWED_USE",
    "RETENTION_AND_DELETION_OBLIGATIONS",
    "TRAINING_USE_PROHIBITION",
)
MANIFEST_REVIEW_GATE_ORDER: tuple[ManifestReviewGate, ...] = (
    "PROVENANCE_AND_CANDIDATE_CLOSURE",
    "SUBMISSION_TIME_AUTHORIZATION",
    "PROVIDER_TERMS_AT_SUBMISSION",
    "INPUT_TEXT_AND_MEDIA_RIGHTS",
    "OUTPUT_COPYRIGHT_AND_COMMERCIAL_SCOPE",
    "LIKENESS_PRIVACY_AND_SENSITIVE_DATA",
    "BRAND_AND_PROTECTED_CONTENT",
    "TERRITORY_DURATION_AND_ALLOWED_USE",
    "RETENTION_AND_DELETION_OBLIGATIONS",
    "TRAINING_USE_PROHIBITION",
    "REVIEWER_ROLE_AND_EVIDENCE_CLOSURE",
)
CURRENT_STATUS_CATEGORY_ORDER: tuple[CurrentStatusCategory, ...] = (
    "HOLD_ACTIVE",
    "REVOCATION_EFFECTIVE",
    "COMPLAINT_OPEN",
    "DISPUTE_OPEN",
    "RIGHTS_BASIS_CURRENT",
    "IDENTITY_BINDING_CURRENT",
    "PROVIDER_TERMS_COMPATIBILITY_CURRENT",
    "RETENTION_DELETION_COMPLIANCE_CURRENT",
    "TRAINING_USE_PROHIBITION_CURRENT",
)
CURRENT_STATUS_ADVERSE_CATEGORY_ORDER = CURRENT_STATUS_CATEGORY_ORDER[:4]
CURRENT_STATUS_POSITIVE_CATEGORY_ORDER = CURRENT_STATUS_CATEGORY_ORDER[4:]
CURRENT_STATUS_LIMITATION_CODE_ORDER: tuple[CurrentStatusLimitationCode, ...] = (
    "SOURCE_AUTHENTICITY_NOT_PROVEN",
    "SOURCE_COMPLETENESS_NOT_PROVEN",
    "CHAIN_COMPLETENESS_NOT_PROVEN",
    "REALITY_CURRENTNESS_NOT_PROVEN",
    "SCOPE_LIMITED_TO_DECLARED_SUBJECT",
    "TIME_WINDOW_LIMITED",
    "LEGAL_EFFECT_NOT_DETERMINED",
)

_QUALIFICATION_GATE_EVIDENCE_CATEGORIES: tuple[tuple[str, ...], ...] = (
    (
        "PROVIDER_ATTEMPT_PROVENANCE",
        "PROVIDER_TERMINAL_OBSERVATION",
        "INPUT_TEXT_AND_MEDIA_RIGHTS_AT_SUBMISSION",
        "PROVIDER_TERMS_AT_SUBMISSION",
        "OUTPUT_COPYRIGHT_AND_COMMERCIAL_SCOPE",
        "LIKENESS_PRIVACY_AND_SENSITIVE_DATA",
        "BRAND_AND_PROTECTED_CONTENT",
        "REMOTE_PROCESSING_AUTHORIZATION_AT_SUBMISSION",
        "RETENTION_POLICY_AT_SUBMISSION",
        "TRAINING_USE_POLICY_AT_SUBMISSION",
    ),
    (),
    ("PROVIDER_ATTEMPT_PROVENANCE", "PROVIDER_TERMINAL_OBSERVATION"),
    (),
    ("INPUT_TEXT_AND_MEDIA_RIGHTS_AT_SUBMISSION",),
    (
        "INPUT_TEXT_AND_MEDIA_RIGHTS_AT_SUBMISSION",
        "LIKENESS_PRIVACY_AND_SENSITIVE_DATA",
    ),
    ("INPUT_TEXT_AND_MEDIA_RIGHTS_AT_SUBMISSION",),
    ("PROVIDER_ATTEMPT_PROVENANCE", "PROVIDER_TERMINAL_OBSERVATION"),
    ("PROVIDER_TERMS_AT_SUBMISSION",),
    ("OUTPUT_COPYRIGHT_AND_COMMERCIAL_SCOPE",),
    ("LIKENESS_PRIVACY_AND_SENSITIVE_DATA",),
    ("BRAND_AND_PROTECTED_CONTENT",),
    (
        "PROVIDER_ATTEMPT_PROVENANCE",
        "REMOTE_PROCESSING_AUTHORIZATION_AT_SUBMISSION",
    ),
    ("PROVIDER_TERMS_AT_SUBMISSION", "RETENTION_POLICY_AT_SUBMISSION"),
    ("PROVIDER_TERMS_AT_SUBMISSION", "TRAINING_USE_POLICY_AT_SUBMISSION"),
)


class GeneratedReferenceRightsCurrentStatusError(ValueError):
    """The ADR-044 deterministic boundary failed closed."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


class GeneratedReferenceChainReplayError(GeneratedReferenceRightsCurrentStatusError):
    """One explicit logical chain failed structural replay."""


class GeneratedReferenceChainCoverageError(GeneratedReferenceRightsCurrentStatusError):
    """The explicit chain set failed Request coverage."""

    def __init__(self, code: str, message: str, *, replay_code: str | None = None) -> None:
        self.replay_code = replay_code
        super().__init__(code, message)


class GeneratedReferenceJointReplayError(GeneratedReferenceRightsCurrentStatusError):
    """Evidence Record reconstruction failed."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        coverage_code: str | None = None,
        replay_code: str | None = None,
    ) -> None:
        self.coverage_code = coverage_code
        self.replay_code = replay_code
        super().__init__(code, message)


class GeneratedReferenceAsOfAssessmentError(GeneratedReferenceRightsCurrentStatusError):
    """Historical as-of assessment failed."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        joint_replay_code: str | None = None,
        coverage_code: str | None = None,
        replay_code: str | None = None,
    ) -> None:
        self.joint_replay_code = joint_replay_code
        self.coverage_code = coverage_code
        self.replay_code = replay_code
        super().__init__(code, message)


class GeneratedReferenceReceiptError(GeneratedReferenceRightsCurrentStatusError):
    """Receipt creation or same-call verification failed."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        assessment_code: str | None = None,
        joint_replay_code: str | None = None,
        coverage_code: str | None = None,
        replay_code: str | None = None,
    ) -> None:
        self.assessment_code = assessment_code
        self.joint_replay_code = joint_replay_code
        self.coverage_code = coverage_code
        self.replay_code = replay_code
        super().__init__(code, message)


def _invalid(message: str) -> NoReturn:
    raise ValueError(message)


def _canonical_string(value: str, *, field: str) -> str:
    if type(value) is not str:
        _invalid(f"{field} must be an exact string")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{field} must contain Unicode scalar values") from exc
    if unicodedata.normalize("NFC", value) != value:
        _invalid(f"{field} must already use Unicode NFC")
    if value.startswith("\ufeff") or "\r" in value:
        _invalid(f"{field} contains a BOM or CR")
    return value


def _human_text(value: str, *, field: str) -> str:
    value = _canonical_string(value, field=field)
    if value != value.strip() or not 1 <= len(value) <= 1000:
        _invalid(f"{field} must contain 1..1000 trimmed code points")
    for character in value:
        if unicodedata.category(character) in {"Cc", "Cs"}:
            _invalid(f"{field} contains a prohibited control character")
    return value


def _parse_utc(value: str, *, field: str) -> datetime:
    _canonical_string(value, field=field)
    if re.fullmatch(_UTC_SECONDS_PATTERN, value) is None:
        _invalid(f"{field} must be a UTC second timestamp")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError as exc:
        raise ValueError(f"{field} is not a real UTC timestamp") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        _invalid(f"{field} must use canonical UTC seconds")
    return parsed


def _utc_seconds(value: str, *, field: str) -> str:
    _parse_utc(value, field=field)
    return value


def _finite_or_perpetual(value: str, *, field: str) -> str:
    if value == "PERPETUAL":
        return value
    return _utc_seconds(value, field=field)


def _upper_bound(value: str, *, field: str) -> datetime:
    if value == "PERPETUAL":
        return datetime.max.replace(tzinfo=UTC)
    return _parse_utc(value, field=field)


def _validate_json_tree(value: object, *, field: str = "value", depth: int = 1) -> None:
    if depth > _MAX_JSON_DEPTH:
        _invalid(f"{field} exceeds maximum depth")
    if value is None or type(value) in {bool, int, str}:
        if type(value) is str:
            _canonical_string(value, field=field)
        return
    if type(value) is float:
        _invalid(f"{field} contains a floating-point value")
    if type(value) in {list, tuple}:
        items = cast(Sequence[object], value)
        if len(items) > _MAX_CONTAINER_ITEMS:
            _invalid(f"{field} has too many items")
        for index, item in enumerate(items):
            _validate_json_tree(item, field=f"{field}[{index}]", depth=depth + 1)
        return
    if type(value) is dict:
        mapping = cast(dict[str, object], value)
        maximum = _MAX_FORMAL_ROOT_ITEMS if depth == 1 else _MAX_CONTAINER_ITEMS
        if len(mapping) > maximum:
            _invalid(f"{field} has too many members")
        for key, item in mapping.items():
            _canonical_string(key, field=f"{field} key")
            _validate_json_tree(item, field=f"{field}.{key}", depth=depth + 1)
        return
    _invalid(f"{field} is outside the canonical JSON type set")


def _compact_json(value: object) -> bytes:
    _validate_json_tree(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _formal_json(value: object) -> bytes:
    _validate_json_tree(value)
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            separators=(",", ": "),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _semantic_sha256(domain: bytes, projection: object) -> str:
    return hashlib.sha256(domain + _compact_json(projection)).hexdigest()


def _raw_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _json_no_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            _invalid(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _exact_json_equal(left: object, right: object) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is list:
        left_items = cast(list[object], left)
        right_items = cast(list[object], right)
        return len(left_items) == len(right_items) and all(
            _exact_json_equal(a, b) for a, b in zip(left_items, right_items, strict=True)
        )
    if type(left) is dict:
        left_map = cast(dict[str, object], left)
        right_map = cast(dict[str, object], right)
        return left_map.keys() == right_map.keys() and all(
            _exact_json_equal(left_map[key], right_map[key]) for key in left_map
        )
    return left == right


def _json_arrays_to_tuples(value: object) -> object:
    """Adapt canonical JSON arrays to this module's frozen tuple Contract fields.

    Python callers remain subject to strict ``model_validate`` input types.  This adapter is
    reachable only after the dedicated canonical-JSON parser has rejected duplicate keys,
    non-finite values, invalid UTF-8 and non-canonical bytes.  Every portable collection in the
    ADR-044 Contract family is a frozen tuple, so JSON arrays have one unambiguous Python form.
    """

    if type(value) is list:
        return tuple(_json_arrays_to_tuples(item) for item in cast(list[object], value))
    if type(value) is dict:
        return {
            key: _json_arrays_to_tuples(item)
            for key, item in cast(dict[str, object], value).items()
        }
    return value


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
    )
    _root_json_max_items: ClassVar[int] = _MAX_FORMAL_ROOT_ITEMS

    @model_validator(mode="before")
    @classmethod
    def _reject_subclass_instance(cls, value: object) -> object:
        if isinstance(value, cls) and type(value) is not cls:
            _invalid(f"{cls.__name__} subclasses are not admitted")
        return value

    @classmethod
    def model_validate_json(cls, json_data: str | bytes | bytearray, **kwargs: object) -> Self:
        if kwargs:
            _invalid("model_validate_json options are not supported")
        if type(json_data) is str:
            raw = json_data.encode("utf-8")
        elif type(json_data) is bytes:
            raw = json_data
        else:
            raw = bytes(cast(bytearray, json_data))
        if len(raw) > _MAX_FORMAL_DOCUMENT_BYTES:
            _invalid("formal document exceeds byte limit")
        if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw or not raw.endswith(b"\n"):
            _invalid("formal JSON must be UTF-8 without BOM/CR and end in one LF")
        try:
            decoded = raw.decode("utf-8")
            parsed = json.loads(
                decoded,
                object_pairs_hook=_json_no_duplicates,
                parse_constant=lambda value: _invalid(f"non-finite number: {value}"),
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("formal JSON is invalid") from exc
        _validate_json_tree(parsed)
        validated = cls.model_validate(_json_arrays_to_tuples(parsed))
        projected = _explicit_value(validated)
        if not _exact_json_equal(parsed, projected):
            _invalid("formal JSON changes value under strict Contract admission")
        if _formal_json(projected) != raw:
            _invalid("formal JSON is not canonical")
        return validated


class _ZeroAuthorityModel(_StrictFrozenModel):
    authority_scope: Literal["THIS_DOCUMENT_GRANTS_NO_PROVIDER_RUNTIME_OR_ASSET_USE_AUTHORITY"]
    current_gate: Literal["HUMAN_GATE"]
    provider_state: Literal["NOT_AUTHORIZED"]
    generation_authorized: Literal[False]
    execution_authorized: Literal[False]
    publication_authorized: Literal[False]
    remote_processing_allowed: Literal[False]
    retention_allowed: Literal[False]
    training_allowed: Literal[False]
    publication_allowed: Literal[False]
    automated_execution_allowed: Literal[False]
    authorized_attempts: Literal[0]
    authorized_cost_cny: Literal[0]
    posts_allowed: Literal[0]
    provider_requests: Literal[0]
    grants_rights: Literal[False]
    grants_qualification: Literal[False]
    grants_execution_authority: Literal[False]
    eligible_for_asset_promotion: Literal[False]
    replaces_rights_manifest: Literal[False]
    usage_restriction: Literal["MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION"]

    @model_validator(mode="before")
    @classmethod
    def _exact_authority_scalars(cls, value: object) -> object:
        if type(value) is dict:
            mapping = cast(dict[str, object], value)
            for field_name in (
                "generation_authorized",
                "execution_authorized",
                "publication_authorized",
                "remote_processing_allowed",
                "retention_allowed",
                "training_allowed",
                "publication_allowed",
                "automated_execution_allowed",
                "grants_rights",
                "grants_qualification",
                "grants_execution_authority",
                "eligible_for_asset_promotion",
                "replaces_rights_manifest",
            ):
                if field_name in mapping and type(mapping[field_name]) is not bool:
                    _invalid(f"{field_name} must be an exact JSON boolean")
            for field_name in (
                "authorized_attempts",
                "authorized_cost_cny",
                "posts_allowed",
                "provider_requests",
            ):
                if field_name in mapping and type(mapping[field_name]) is not int:
                    _invalid(f"{field_name} must be an exact JSON integer")
        return value


_ZERO_AUTHORITY_VALUES: dict[str, object] = {
    "authority_scope": "THIS_DOCUMENT_GRANTS_NO_PROVIDER_RUNTIME_OR_ASSET_USE_AUTHORITY",
    "current_gate": "HUMAN_GATE",
    "provider_state": "NOT_AUTHORIZED",
    "generation_authorized": False,
    "execution_authorized": False,
    "publication_authorized": False,
    "remote_processing_allowed": False,
    "retention_allowed": False,
    "training_allowed": False,
    "publication_allowed": False,
    "automated_execution_allowed": False,
    "authorized_attempts": 0,
    "authorized_cost_cny": 0,
    "posts_allowed": 0,
    "provider_requests": 0,
    "grants_rights": False,
    "grants_qualification": False,
    "grants_execution_authority": False,
    "eligible_for_asset_promotion": False,
    "replaces_rights_manifest": False,
    "usage_restriction": "MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION",
}


def _zero_authority_values() -> dict[str, object]:
    return dict(_ZERO_AUTHORITY_VALUES)


class GeneratedReferenceRightsManifestEvidenceReferenceV1(_StrictFrozenModel):
    ordinal: Annotated[int, Field(ge=0, le=8)]
    category: ManifestEvidenceCategory
    record_id: PortableId
    document_profile: PortableId
    document_sha256: LowerSha256
    document_size_bytes: Annotated[int, Field(ge=1, le=262_144)]
    media_type: Annotated[str, Field(pattern=_MEDIA_TYPE_PATTERN)]
    observed_at: str
    effective_from: str
    effective_until: str
    evidence_valid_until: str

    @field_validator("observed_at", "effective_from")
    @classmethod
    def _times(cls, value: str, info: ValidationInfo) -> str:
        return _utc_seconds(value, field=str(info.field_name))

    @field_validator("effective_until", "evidence_valid_until")
    @classmethod
    def _upper_bounds(cls, value: str, info: ValidationInfo) -> str:
        return _finite_or_perpetual(value, field=str(info.field_name))

    @model_validator(mode="before")
    @classmethod
    def _exact_counts(cls, value: object) -> object:
        if type(value) is dict:
            mapping = cast(dict[str, object], value)
            for field_name in ("ordinal", "document_size_bytes"):
                if field_name in mapping and type(mapping[field_name]) is not int:
                    _invalid(f"{field_name} must be an exact JSON integer")
        return value

    @model_validator(mode="after")
    def _window(self) -> Self:
        if not (
            _parse_utc(self.effective_from, field="effective_from")
            <= _parse_utc(self.observed_at, field="observed_at")
            < _upper_bound(self.effective_until, field="effective_until")
        ):
            _invalid("Manifest evidence observation must lie in its effective window")
        if _upper_bound(self.evidence_valid_until, field="evidence_valid_until") > _upper_bound(
            self.effective_until, field="effective_until"
        ):
            _invalid("evidence_valid_until cannot follow effective_until")
        return self


@dataclass(frozen=True, slots=True)
class GeneratedReferenceRightsManifestEvidenceInput:
    reference: GeneratedReferenceRightsManifestEvidenceReferenceV1
    document_bytes: bytes


class GeneratedReferenceRightsManifestGateResultV1(_StrictFrozenModel):
    ordinal: Annotated[int, Field(ge=0, le=10)]
    gate: ManifestReviewGate
    result: ManifestGateResult
    evidence_record_ids: Annotated[tuple[PortableId, ...], Field(max_length=1)]
    basis: HumanBasis

    @field_validator("basis")
    @classmethod
    def _basis(cls, value: str) -> str:
        return _human_text(value, field="basis")

    @model_validator(mode="before")
    @classmethod
    def _ordinal_type(cls, value: object) -> object:
        if type(value) is dict and "ordinal" in cast(dict[str, object], value):
            if type(cast(dict[str, object], value)["ordinal"]) is not int:
                _invalid("ordinal must be an exact JSON integer")
        return value


class GeneratedReferenceRightsScopeProposalV1(_StrictFrozenModel):
    territory_scope: Annotated[tuple[PortableCode, ...], Field(min_length=1, max_length=64)]
    allowed_use_scope: Annotated[tuple[PortableCode, ...], Field(min_length=1, max_length=32)]
    proposed_scope_valid_until: str

    @field_validator("territory_scope", "allowed_use_scope")
    @classmethod
    def _canonical_codes(cls, value: tuple[str, ...], info: ValidationInfo) -> tuple[str, ...]:
        if len(value) != len(set(value)) or value != tuple(
            sorted(value, key=lambda item: item.encode("utf-8"))
        ):
            _invalid(f"{info.field_name} must be unique and strictly ascending by UTF-8 bytes")
        return value

    @field_validator("proposed_scope_valid_until")
    @classmethod
    def _until(cls, value: str) -> str:
        return _utc_seconds(value, field="proposed_scope_valid_until")


class GeneratedReferenceReviewedRightsScopeV1(_StrictFrozenModel):
    territory_scope: Annotated[tuple[PortableCode, ...], Field(min_length=1, max_length=64)]
    allowed_use_scope: Annotated[tuple[PortableCode, ...], Field(min_length=1, max_length=32)]
    reviewed_scope_valid_until: str
    output_copyright_and_commercial_scope_basis: HumanBasis
    likeness_privacy_and_sensitive_data_basis: HumanBasis
    brand_and_protected_content_basis: HumanBasis
    retention_and_deletion_basis: HumanBasis
    training_use_prohibition_basis: HumanBasis
    review_basis: HumanBasis

    @field_validator("territory_scope", "allowed_use_scope")
    @classmethod
    def _canonical_codes(cls, value: tuple[str, ...], info: ValidationInfo) -> tuple[str, ...]:
        if len(value) != len(set(value)) or value != tuple(
            sorted(value, key=lambda item: item.encode("utf-8"))
        ):
            _invalid(f"{info.field_name} must be unique and strictly ascending by UTF-8 bytes")
        return value

    @field_validator("reviewed_scope_valid_until")
    @classmethod
    def _until(cls, value: str) -> str:
        return _utc_seconds(value, field="reviewed_scope_valid_until")

    @field_validator(
        "output_copyright_and_commercial_scope_basis",
        "likeness_privacy_and_sensitive_data_basis",
        "brand_and_protected_content_basis",
        "retention_and_deletion_basis",
        "training_use_prohibition_basis",
        "review_basis",
    )
    @classmethod
    def _bases(cls, value: str, info: ValidationInfo) -> str:
        return _human_text(value, field=str(info.field_name))


class GeneratedReferenceCurrentStatusSubjectClosureV1(_StrictFrozenModel):
    closure_profile: Literal["sdc.generated-reference-current-status-subject-closure.v1"]
    closure_id: Annotated[
        str, Field(pattern=r"^generated_reference_current_status_subject_closure_v1_[0-9a-f]{20}$")
    ]
    closure_sha256: LowerSha256
    policy_id: Literal["sdc.generated-reference-current-status-policy"]
    policy_version: Literal["1.0.0"]
    policy_document_sha256: Literal[
        "cf596012ca0d3bf88d1e49d0aea11184428d047d0e919822032da51f792d61e0"
    ]
    reference_prompt_artifact_sha256: LowerSha256
    provider_attempt_outcome_id: PortableId
    provider_attempt_outcome_sha256: LowerSha256
    candidate_id: PortableId
    candidate_sha256: LowerSha256
    qualification_request_id: PortableId
    qualification_request_sha256: LowerSha256
    qualification_decision_id: PortableId
    qualification_decision_sha256: LowerSha256
    manifest_id: PortableId
    manifest_sha256: LowerSha256
    subject_id: PortableId
    asset_purpose: AssetPurpose
    media_content_sha256: LowerSha256
    manifest_at: str
    manifest_valid_until: str

    @field_validator("manifest_at", "manifest_valid_until")
    @classmethod
    def _times(cls, value: str, info: ValidationInfo) -> str:
        return _utc_seconds(value, field=str(info.field_name))

    @model_validator(mode="after")
    def _identity(self) -> Self:
        _validate_identity(
            self,
            id_field="closure_id",
            sha_field="closure_sha256",
            stem="generated_reference_current_status_subject_closure_v1_",
            domain=GENERATED_REFERENCE_CURRENT_STATUS_SUBJECT_CLOSURE_SHA256_DOMAIN,
        )
        if _parse_utc(self.manifest_at, field="manifest_at") >= _parse_utc(
            self.manifest_valid_until, field="manifest_valid_until"
        ):
            _invalid("Manifest validity window must be non-empty")
        return self


class GeneratedReferenceCurrentStatusObservationRefV1(_StrictFrozenModel):
    ordinal: Annotated[int, Field(ge=0, le=31)]
    observation_id: Annotated[
        str,
        Field(pattern=r"^generated_reference_current_status_source_observation_v1_[0-9a-f]{20}$"),
    ]
    observation_sha256: LowerSha256
    category: CurrentStatusCategory
    source_identity_ref_sha256: LowerSha256
    chain_scope_sha256: LowerSha256
    chain_sha256: LowerSha256
    valid_from: str
    valid_until: str

    @field_validator("valid_from", "valid_until")
    @classmethod
    def _times(cls, value: str, info: ValidationInfo) -> str:
        return _utc_seconds(value, field=str(info.field_name))

    @model_validator(mode="before")
    @classmethod
    def _ordinal_type(cls, value: object) -> object:
        if type(value) is dict and "ordinal" in cast(dict[str, object], value):
            if type(cast(dict[str, object], value)["ordinal"]) is not int:
                _invalid("ordinal must be an exact JSON integer")
        return value

    @model_validator(mode="after")
    def _window(self) -> Self:
        if _parse_utc(self.valid_from, field="valid_from") >= _parse_utc(
            self.valid_until, field="valid_until"
        ):
            _invalid("Observation reference validity window must be non-empty")
        return self


class GeneratedReferenceCurrentStatusChainHeadRefV1(_StrictFrozenModel):
    observation_id: Annotated[
        str,
        Field(pattern=r"^generated_reference_current_status_source_observation_v1_[0-9a-f]{20}$"),
    ]
    observation_sha256: LowerSha256
    chain_sha256: LowerSha256


class GeneratedReferenceCurrentStatusChainLinkV1(_StrictFrozenModel):
    link_kind: CurrentStatusLinkKind
    chain_scope_sha256: LowerSha256
    predecessor_heads: Annotated[
        tuple[GeneratedReferenceCurrentStatusChainHeadRefV1, ...], Field(max_length=8)
    ]

    @model_validator(mode="after")
    def _cardinality_and_order(self) -> Self:
        expected = {"GENESIS": 0, "SUCCESSOR": 1}
        if self.link_kind in expected and len(self.predecessor_heads) != expected[self.link_kind]:
            _invalid(f"{self.link_kind} has invalid predecessor cardinality")
        if self.link_kind == "RECONCILIATION" and not 2 <= len(self.predecessor_heads) <= 8:
            _invalid("RECONCILIATION requires 2..8 predecessor heads")
        keys = tuple(
            (item.observation_id, item.observation_sha256, item.chain_sha256)
            for item in self.predecessor_heads
        )
        if len(keys) != len(set(keys)):
            _invalid("predecessor heads must be unique")
        if self.link_kind == "RECONCILIATION" and keys != tuple(sorted(keys)):
            _invalid("reconciliation predecessor heads are not in canonical order")
        return self


class GeneratedReferenceCurrentStatusCategoryResultV1(_StrictFrozenModel):
    ordinal: Annotated[int, Field(ge=0, le=8)]
    category: CurrentStatusCategory
    claim_value: CurrentStatusClaimValue
    deterministic_effect: CurrentStatusDeterministicEffect
    category_observation_refs: Annotated[
        tuple[GeneratedReferenceCurrentStatusObservationRefV1, ...],
        Field(min_length=1, max_length=32),
    ]
    relied_on_observation_refs: Annotated[
        tuple[GeneratedReferenceCurrentStatusObservationRefV1, ...], Field(max_length=32)
    ]
    result_valid_until: str

    @field_validator("result_valid_until")
    @classmethod
    def _until(cls, value: str) -> str:
        return _utc_seconds(value, field="result_valid_until")

    @model_validator(mode="before")
    @classmethod
    def _ordinal_type(cls, value: object) -> object:
        if type(value) is dict and "ordinal" in cast(dict[str, object], value):
            if type(cast(dict[str, object], value)["ordinal"]) is not int:
                _invalid("ordinal must be an exact JSON integer")
        return value

    @model_validator(mode="after")
    def _membership(self) -> Self:
        if any(item.category != self.category for item in self.category_observation_refs):
            _invalid("category_observation_refs contains another category")
        category_keys = tuple(_observation_ref_key(item) for item in self.category_observation_refs)
        relied_keys = tuple(_observation_ref_key(item) for item in self.relied_on_observation_refs)
        if len(category_keys) != len(set(category_keys)) or len(relied_keys) != len(
            set(relied_keys)
        ):
            _invalid("category result references must be unique")
        iterator = iter(category_keys)
        if not all(any(candidate == key for candidate in iterator) for key in relied_keys):
            _invalid("relied_on_observation_refs must be a stable subsequence")
        return self


class CreativeSampleGeneratedReferenceRightsManifestV1(_ZeroAuthorityModel):
    schema_version: Literal["1.0.0"]
    document_type: Literal["sdc.creative-sample-generated-reference-rights-manifest-v1"]
    manifest_scope: Literal["GENERATED_REFERENCE_RIGHTS_REVIEW_ONLY"]
    manifest_id: Annotated[
        str, Field(pattern=r"^generated_reference_rights_manifest_v1_[0-9a-f]{20}$")
    ]
    manifest_sha256: LowerSha256
    policy_id: Literal["sdc.generated-reference-rights-manifest-policy"]
    policy_version: Literal["1.0.0"]
    policy_document_sha256: Literal[
        "7d9f72f134b5be5f68bb55f25ee898736bd84d39b2ff6917e0e2ecab447f8f16"
    ]
    manifest_review_payload_sha256: LowerSha256
    reference_prompt_artifact_sha256: LowerSha256
    provider_attempt_outcome_id: PortableId
    provider_attempt_outcome_sha256: LowerSha256
    candidate_id: PortableId
    candidate_sha256: LowerSha256
    qualification_request_id: PortableId
    qualification_request_sha256: LowerSha256
    qualification_decision_id: PortableId
    qualification_decision_sha256: LowerSha256
    subject_id: PortableId
    asset_purpose: AssetPurpose
    profile_id: PortableId
    profile_version: SemanticVersion
    profile_sha256: LowerSha256
    catalog_version: SemanticVersion
    catalog_sha256: LowerSha256
    render_input_sha256: LowerSha256
    prompt_sha256: LowerSha256
    prompt_size_bytes: Annotated[int, Field(ge=1, le=65_536)]
    prompt_render_receipt_sha256: LowerSha256
    media_content_sha256: LowerSha256
    media_size_bytes: Annotated[int, Field(ge=1, le=67_108_864)]
    media_technical_record_sha256: LowerSha256
    provider: PortableId
    model: PortableId
    provider_region: PortableId
    provider_terms_snapshot_id: PortableId
    provider_terms_snapshot_sha256: LowerSha256
    submitted_at: str
    qualification_decision_at: str
    qualification_valid_until: str
    manifest_at: str
    manifest_valid_until: str
    review_evidence_refs: Annotated[
        tuple[GeneratedReferenceRightsManifestEvidenceReferenceV1, ...],
        Field(min_length=9, max_length=9),
    ]
    gate_results: Annotated[
        tuple[GeneratedReferenceRightsManifestGateResultV1, ...],
        Field(min_length=11, max_length=11),
    ]
    proposed_rights_scope: GeneratedReferenceRightsScopeProposalV1
    reviewed_rights_scope: GeneratedReferenceReviewedRightsScopeV1
    maker_identity_ref_sha256: LowerSha256
    maker_action_sha256: LowerSha256
    maker_prepared_at: str
    checker_identity_ref_sha256: LowerSha256
    checker_action_sha256: LowerSha256
    checker_reviewed_at: str
    rights_review_performed: Literal[True]
    eligible_for_separate_generated_current_status_review: Literal[True]
    current_status_assessment_embedded: Literal[False]
    status: Literal["GENERATED_RIGHTS_MANIFEST_RECORDED"]
    evidence_scope: Literal["EXPLICIT_FINITE_BOUND_SET_ONLY"]

    @field_validator(
        "submitted_at",
        "qualification_decision_at",
        "qualification_valid_until",
        "manifest_at",
        "manifest_valid_until",
        "maker_prepared_at",
        "checker_reviewed_at",
    )
    @classmethod
    def _times(cls, value: str, info: ValidationInfo) -> str:
        return _utc_seconds(value, field=str(info.field_name))

    @model_validator(mode="after")
    def _closure(self) -> Self:
        _validate_identity(
            self,
            id_field="manifest_id",
            sha_field="manifest_sha256",
            stem="generated_reference_rights_manifest_v1_",
            domain=GENERATED_REFERENCE_RIGHTS_MANIFEST_SHA256_DOMAIN,
        )
        if tuple(
            item.category for item in self.review_evidence_refs
        ) != MANIFEST_REVIEW_EVIDENCE_CATEGORY_ORDER or tuple(
            item.ordinal for item in self.review_evidence_refs
        ) != tuple(range(9)):
            _invalid("review_evidence_refs must use exact policy order and ordinals")
        if tuple(item.gate for item in self.gate_results) != MANIFEST_REVIEW_GATE_ORDER or tuple(
            item.ordinal for item in self.gate_results
        ) != tuple(range(11)):
            _invalid("gate_results must use exact policy order and ordinals")
        if any(item.result != "PASS" for item in self.gate_results):
            _invalid("a portable Rights Manifest requires all PASS results")
        record_ids = tuple(item.record_id for item in self.review_evidence_refs)
        expected_gate_ids = ((),) + tuple((item,) for item in record_ids) + ((),)
        if tuple(item.evidence_record_ids for item in self.gate_results) != expected_gate_ids:
            _invalid("gate evidence membership is not the frozen mapping")
        if (
            self.gate_results[0].basis != "COMPILER_REVALIDATED_EXACT_ADR042_ADR043_CLOSURE"
            or self.gate_results[10].basis
            != "COMPILER_REVALIDATED_DISTINCT_ROLE_AND_ACTION_CLOSURE"
        ):
            _invalid("compiler-derived gate basis drift")
        reviewed = self.reviewed_rights_scope
        proposed = self.proposed_rights_scope
        if not set(reviewed.territory_scope).issubset(proposed.territory_scope) or not set(
            reviewed.allowed_use_scope
        ).issubset(proposed.allowed_use_scope):
            _invalid("reviewed Rights scope must be a subset of proposed scope")
        expected_bases = (
            self.gate_results[4].basis,
            self.gate_results[5].basis,
            self.gate_results[6].basis,
            self.gate_results[8].basis,
            self.gate_results[9].basis,
        )
        actual_bases = (
            reviewed.output_copyright_and_commercial_scope_basis,
            reviewed.likeness_privacy_and_sensitive_data_basis,
            reviewed.brand_and_protected_content_basis,
            reviewed.retention_and_deletion_basis,
            reviewed.training_use_prohibition_basis,
        )
        if actual_bases != expected_bases:
            _invalid("reviewed-scope basis does not match gate basis")
        decision_at = _parse_utc(self.qualification_decision_at, field="qualification_decision_at")
        maker_at = _parse_utc(self.maker_prepared_at, field="maker_prepared_at")
        manifest_at = _parse_utc(self.manifest_at, field="manifest_at")
        if (
            not decision_at <= maker_at <= manifest_at
            or self.manifest_at != self.checker_reviewed_at
        ):
            _invalid("Manifest action-time rule failed")
        if not manifest_at < _parse_utc(
            self.qualification_valid_until, field="qualification_valid_until"
        ):
            _invalid("Manifest was not recorded within Qualification validity")
        if not manifest_at < _parse_utc(self.manifest_valid_until, field="manifest_valid_until"):
            _invalid("Manifest validity window must be non-empty")
        if reviewed.reviewed_scope_valid_until > proposed.proposed_scope_valid_until:
            _invalid("reviewed scope cannot outlive proposed scope")
        if self.maker_identity_ref_sha256 == self.checker_identity_ref_sha256:
            _invalid("Manifest Maker and Checker identities must be distinct")
        if self.maker_action_sha256 == self.checker_action_sha256:
            _invalid("Manifest Maker and Checker actions must be distinct")
        if len({item.record_id for item in self.review_evidence_refs}) != 9:
            _invalid("Manifest evidence record IDs must be unique")
        submitted_at = _parse_utc(self.submitted_at, field="submitted_at")
        for evidence in self.review_evidence_refs[:2]:
            if not (
                _parse_utc(evidence.effective_from, field="effective_from")
                <= submitted_at
                < _upper_bound(evidence.effective_until, field="effective_until")
            ):
                _invalid("historical Manifest evidence was not effective at submission")
        finite_bounds = [manifest_at + timedelta(seconds=86_400)]
        for evidence in self.review_evidence_refs[2:]:
            if not (
                _parse_utc(evidence.observed_at, field="observed_at") <= manifest_at
                and _parse_utc(evidence.effective_from, field="effective_from")
                <= manifest_at
                < _upper_bound(evidence.effective_until, field="effective_until")
                and manifest_at
                < _upper_bound(evidence.evidence_valid_until, field="evidence_valid_until")
            ):
                _invalid("current-facing Manifest evidence is not usable at manifest_at")
            for bound_name, bound in (
                ("effective_until", evidence.effective_until),
                ("evidence_valid_until", evidence.evidence_valid_until),
            ):
                if bound != "PERPETUAL":
                    finite_bounds.append(_parse_utc(bound, field=bound_name))
        finite_bounds.append(
            _parse_utc(reviewed.reviewed_scope_valid_until, field="reviewed_scope_valid_until")
        )
        expected_manifest_until = min(finite_bounds).strftime("%Y-%m-%dT%H:%M:%SZ")
        if self.manifest_valid_until != expected_manifest_until:
            _invalid("manifest_valid_until is not uniquely derived")
        expected_payload_sha = _semantic_sha256(
            GENERATED_REFERENCE_RIGHTS_MANIFEST_REVIEW_PAYLOAD_SHA256_DOMAIN,
            generated_reference_rights_manifest_review_payload_projection(self),
        )
        if self.manifest_review_payload_sha256 != expected_payload_sha:
            _invalid("manifest_review_payload_sha256 does not bind the closed private projection")
        return self


class CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1(_ZeroAuthorityModel):
    schema_version: Literal["1.0.0"]
    document_type: Literal[
        "sdc.creative-sample-generated-reference-current-status-source-observation-v1"
    ]
    observation_scope: Literal["GENERATED_REFERENCE_CURRENT_STATUS_SOURCE_EVIDENCE_ONLY"]
    observation_profile: Literal["sdc.generated-reference-current-status-observation-profile.v1"]
    observation_id: Annotated[
        str,
        Field(pattern=r"^generated_reference_current_status_source_observation_v1_[0-9a-f]{20}$"),
    ]
    observation_sha256: LowerSha256
    policy_id: Literal["sdc.generated-reference-current-status-policy"]
    policy_version: Literal["1.0.0"]
    policy_document_sha256: Literal[
        "cf596012ca0d3bf88d1e49d0aea11184428d047d0e919822032da51f792d61e0"
    ]
    subject_closure: GeneratedReferenceCurrentStatusSubjectClosureV1
    category: CurrentStatusCategory
    claim_value: CurrentStatusClaimValue
    source_kind: CurrentStatusSourceKind
    basis_code: CurrentStatusBasisCode
    basis_note: HumanBasis
    source_identity_ref_sha256: LowerSha256
    source_object_ref: PortableId
    source_object_sha256: LowerSha256
    source_object_size_bytes: Annotated[int, Field(ge=1, le=262_144)]
    source_object_media_type: Annotated[str, Field(pattern=_MEDIA_TYPE_PATTERN)]
    source_event_at: str
    observed_at: str
    valid_from: str
    valid_until: str
    chain_link: GeneratedReferenceCurrentStatusChainLinkV1
    limitation_codes: Annotated[
        tuple[CurrentStatusLimitationCode, ...], Field(min_length=7, max_length=7)
    ]
    status: Literal["GENERATED_CURRENT_STATUS_SOURCE_OBSERVATION_RECORDED"]
    evidence_scope: Literal["EXPLICIT_FINITE_BOUND_SET_ONLY"]

    @field_validator("basis_note")
    @classmethod
    def _basis(cls, value: str) -> str:
        return _human_text(value, field="basis_note")

    @field_validator("source_event_at", "observed_at", "valid_from", "valid_until")
    @classmethod
    def _times(cls, value: str, info: ValidationInfo) -> str:
        return _utc_seconds(value, field=str(info.field_name))

    @model_validator(mode="after")
    def _closure(self) -> Self:
        _validate_identity(
            self,
            id_field="observation_id",
            sha_field="observation_sha256",
            stem="generated_reference_current_status_source_observation_v1_",
            domain=GENERATED_REFERENCE_CURRENT_STATUS_SOURCE_OBSERVATION_SHA256_DOMAIN,
        )
        _validate_observation_semantics(self)
        return self


class CreativeSampleGeneratedReferenceCurrentStatusRequestV1(_ZeroAuthorityModel):
    schema_version: Literal["1.0.0"]
    document_type: Literal["sdc.creative-sample-generated-reference-current-status-request-v1"]
    request_scope: Literal["GENERATED_REFERENCE_CURRENT_STATUS_ASSESSMENT_ONLY"]
    request_id: Annotated[
        str, Field(pattern=r"^generated_reference_current_status_request_v1_[0-9a-f]{20}$")
    ]
    request_sha256: LowerSha256
    policy_id: Literal["sdc.generated-reference-current-status-policy"]
    policy_version: Literal["1.0.0"]
    policy_document_sha256: Literal[
        "cf596012ca0d3bf88d1e49d0aea11184428d047d0e919822032da51f792d61e0"
    ]
    subject_closure: GeneratedReferenceCurrentStatusSubjectClosureV1
    status_preparer_identity_ref_sha256: LowerSha256
    status_preparer_action_sha256: LowerSha256
    requested_at: str
    request_valid_until: str
    observation_refs: Annotated[
        tuple[GeneratedReferenceCurrentStatusObservationRefV1, ...],
        Field(min_length=9, max_length=32),
    ]
    request_basis: HumanBasis
    status: Literal["GENERATED_CURRENT_STATUS_REQUESTED"]
    evidence_scope: Literal["EXPLICIT_FINITE_BOUND_SET_ONLY"]

    @field_validator("requested_at", "request_valid_until")
    @classmethod
    def _times(cls, value: str, info: ValidationInfo) -> str:
        return _utc_seconds(value, field=str(info.field_name))

    @field_validator("request_basis")
    @classmethod
    def _basis(cls, value: str) -> str:
        return _human_text(value, field="request_basis")

    @model_validator(mode="after")
    def _closure(self) -> Self:
        _validate_identity(
            self,
            id_field="request_id",
            sha_field="request_sha256",
            stem="generated_reference_current_status_request_v1_",
            domain=GENERATED_REFERENCE_CURRENT_STATUS_REQUEST_SHA256_DOMAIN,
        )
        _validate_request_refs(self)
        return self


class CreativeSampleGeneratedReferenceCurrentStatusInstructionV1(_ZeroAuthorityModel):
    schema_version: Literal["1.0.0"]
    document_type: Literal["sdc.creative-sample-generated-reference-current-status-instruction-v1"]
    instruction_scope: Literal["GENERATED_REFERENCE_CURRENT_STATUS_ASSESSMENT_ONLY"]
    instruction_id: Annotated[
        str, Field(pattern=r"^generated_reference_current_status_instruction_v1_[0-9a-f]{20}$")
    ]
    instruction_sha256: LowerSha256
    policy_id: Literal["sdc.generated-reference-current-status-policy"]
    policy_version: Literal["1.0.0"]
    policy_document_sha256: Literal[
        "cf596012ca0d3bf88d1e49d0aea11184428d047d0e919822032da51f792d61e0"
    ]
    request_id: PortableId
    request_sha256: LowerSha256
    subject_closure: GeneratedReferenceCurrentStatusSubjectClosureV1
    status_preparer_identity_ref_sha256: LowerSha256
    status_preparer_action_sha256: LowerSha256
    status_checker_identity_ref_sha256: LowerSha256
    status_checker_action_sha256: LowerSha256
    requested_at: str
    request_valid_until: str
    evaluated_at: str
    category_results: Annotated[
        tuple[GeneratedReferenceCurrentStatusCategoryResultV1, ...],
        Field(min_length=9, max_length=9),
    ]
    checker_basis: HumanBasis
    status: Literal["GENERATED_CURRENT_STATUS_INSTRUCTION_RECORDED"]
    evidence_scope: Literal["EXPLICIT_FINITE_BOUND_SET_ONLY"]

    @field_validator("requested_at", "request_valid_until", "evaluated_at")
    @classmethod
    def _times(cls, value: str, info: ValidationInfo) -> str:
        return _utc_seconds(value, field=str(info.field_name))

    @field_validator("checker_basis")
    @classmethod
    def _basis(cls, value: str) -> str:
        return _human_text(value, field="checker_basis")

    @model_validator(mode="after")
    def _closure(self) -> Self:
        _validate_identity(
            self,
            id_field="instruction_id",
            sha_field="instruction_sha256",
            stem="generated_reference_current_status_instruction_v1_",
            domain=GENERATED_REFERENCE_CURRENT_STATUS_INSTRUCTION_SHA256_DOMAIN,
        )
        _validate_category_results(self.category_results)
        return self


class CreativeSampleGeneratedReferenceCurrentStatusDecisionV1(_ZeroAuthorityModel):
    schema_version: Literal["1.0.0"]
    document_type: Literal["sdc.creative-sample-generated-reference-current-status-decision-v1"]
    decision_scope: Literal["GENERATED_REFERENCE_CURRENT_STATUS_ASSESSMENT_ONLY"]
    decision_id: Annotated[
        str, Field(pattern=r"^generated_reference_current_status_decision_v1_[0-9a-f]{20}$")
    ]
    decision_sha256: LowerSha256
    policy_id: Literal["sdc.generated-reference-current-status-policy"]
    policy_version: Literal["1.0.0"]
    policy_document_sha256: Literal[
        "cf596012ca0d3bf88d1e49d0aea11184428d047d0e919822032da51f792d61e0"
    ]
    request_id: PortableId
    request_sha256: LowerSha256
    instruction_id: PortableId
    instruction_sha256: LowerSha256
    subject_closure: GeneratedReferenceCurrentStatusSubjectClosureV1
    evaluated_at: str
    decision_at: str
    status_valid_until: str
    category_results: Annotated[
        tuple[GeneratedReferenceCurrentStatusCategoryResultV1, ...],
        Field(min_length=9, max_length=9),
    ]
    revoked_categories: Annotated[tuple[CurrentStatusCategory, ...], Field(max_length=1)]
    held_categories: Annotated[tuple[CurrentStatusCategory, ...], Field(max_length=8)]
    indeterminate_categories: Annotated[tuple[CurrentStatusCategory, ...], Field(max_length=9)]
    recorded_status: CurrentStatusResult
    status: Literal["GENERATED_CURRENT_STATUS_DECISION_RECORDED"]
    evidence_scope: Literal["EXPLICIT_FINITE_BOUND_SET_ONLY"]

    @field_validator("evaluated_at", "decision_at", "status_valid_until")
    @classmethod
    def _times(cls, value: str, info: ValidationInfo) -> str:
        return _utc_seconds(value, field=str(info.field_name))

    @model_validator(mode="after")
    def _closure(self) -> Self:
        _validate_identity(
            self,
            id_field="decision_id",
            sha_field="decision_sha256",
            stem="generated_reference_current_status_decision_v1_",
            domain=GENERATED_REFERENCE_CURRENT_STATUS_DECISION_SHA256_DOMAIN,
        )
        _validate_decision_semantics(self)
        return self


class CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1(_ZeroAuthorityModel):
    schema_version: Literal["1.0.0"]
    document_type: Literal[
        "sdc.creative-sample-generated-reference-current-status-evidence-record-v1"
    ]
    record_scope: Literal["GENERATED_REFERENCE_CURRENT_STATUS_EVIDENCE_CLOSURE_ONLY"]
    record_id: Annotated[
        str, Field(pattern=r"^generated_reference_current_status_evidence_record_v1_[0-9a-f]{20}$")
    ]
    record_sha256: LowerSha256
    policy_id: Literal["sdc.generated-reference-current-status-policy"]
    policy_version: Literal["1.0.0"]
    policy_document_sha256: Literal[
        "cf596012ca0d3bf88d1e49d0aea11184428d047d0e919822032da51f792d61e0"
    ]
    subject_closure: GeneratedReferenceCurrentStatusSubjectClosureV1
    request: CreativeSampleGeneratedReferenceCurrentStatusRequestV1
    instruction: CreativeSampleGeneratedReferenceCurrentStatusInstructionV1
    decision: CreativeSampleGeneratedReferenceCurrentStatusDecisionV1
    status: Literal["GENERATED_CURRENT_STATUS_EVIDENCE_RECORDED"]
    evidence_scope: Literal["EXPLICIT_FINITE_BOUND_SET_ONLY"]

    @model_validator(mode="after")
    def _closure(self) -> Self:
        _validate_identity(
            self,
            id_field="record_id",
            sha_field="record_sha256",
            stem="generated_reference_current_status_evidence_record_v1_",
            domain=GENERATED_REFERENCE_CURRENT_STATUS_EVIDENCE_RECORD_SHA256_DOMAIN,
        )
        _validate_record_closure(self)
        return self


class CreativeSampleGeneratedReferenceCurrentStatusRecordAsOfAssessmentReceiptV1(
    _ZeroAuthorityModel
):
    schema_version: Literal["1.0.0"]
    document_type: Literal[
        "sdc.creative-sample-generated-reference-current-status-record-as-of-assessment-receipt-v1"
    ]
    receipt_scope: Literal["GENERATED_REFERENCE_CURRENT_STATUS_HISTORICAL_AS_OF_EVIDENCE_ONLY"]
    receipt_id: Annotated[
        str,
        Field(
            pattern=r"^generated_reference_current_status_record_as_of_assessment_receipt_v1_[0-9a-f]{20}$"
        ),
    ]
    receipt_sha256: LowerSha256
    policy_id: Literal["sdc.generated-reference-current-status-policy"]
    policy_version: Literal["1.0.0"]
    policy_document_sha256: Literal[
        "cf596012ca0d3bf88d1e49d0aea11184428d047d0e919822032da51f792d61e0"
    ]
    record_id: PortableId
    record_sha256: LowerSha256
    request_id: PortableId
    request_sha256: LowerSha256
    decision_id: PortableId
    decision_sha256: LowerSha256
    subject_closure: GeneratedReferenceCurrentStatusSubjectClosureV1
    explicit_chain_set_sha256: LowerSha256
    coverage_set_sha256: LowerSha256
    joint_replay_sha256: LowerSha256
    as_of_assessment_sha256: LowerSha256
    as_of: str
    evaluated_at: str
    status_valid_until: str
    window_semantics: Literal["EVALUATED_AT_INCLUSIVE_STATUS_VALID_UNTIL_EXCLUSIVE"]
    recorded_status: CurrentStatusResult
    as_of_status: CurrentStatusResult
    recorded_revoked_categories: Annotated[tuple[CurrentStatusCategory, ...], Field(max_length=1)]
    recorded_held_categories: Annotated[tuple[CurrentStatusCategory, ...], Field(max_length=8)]
    recorded_indeterminate_categories: Annotated[
        tuple[CurrentStatusCategory, ...], Field(max_length=9)
    ]
    record_replay_consistent: Literal[True]
    same_call_assessment_verified: Literal[True]
    historical_assessment_only: Literal[True]
    present_currentness_asserted: Literal[False]
    limitation_codes: Annotated[
        tuple[CurrentStatusLimitationCode, ...], Field(min_length=7, max_length=7)
    ]
    status: Literal["GENERATED_CURRENT_STATUS_AS_OF_RECEIPT_RECORDED"]
    evidence_scope: Literal["EXPLICIT_FINITE_BOUND_SET_ONLY"]

    @field_validator("as_of", "evaluated_at", "status_valid_until")
    @classmethod
    def _times(cls, value: str, info: ValidationInfo) -> str:
        return _utc_seconds(value, field=str(info.field_name))

    @model_validator(mode="after")
    def _closure(self) -> Self:
        _validate_identity(
            self,
            id_field="receipt_id",
            sha_field="receipt_sha256",
            stem="generated_reference_current_status_record_as_of_assessment_receipt_v1_",
            domain=GENERATED_REFERENCE_CURRENT_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_SHA256_DOMAIN,
        )
        if self.limitation_codes != CURRENT_STATUS_LIMITATION_CODE_ORDER:
            _invalid("Receipt limitation_codes must use exact frozen order")
        return self


_ZERO_AUTHORITY_FIELD_NAMES = (
    "authority_scope",
    "current_gate",
    "provider_state",
    "generation_authorized",
    "execution_authorized",
    "publication_authorized",
    "remote_processing_allowed",
    "retention_allowed",
    "training_allowed",
    "publication_allowed",
    "automated_execution_allowed",
    "authorized_attempts",
    "authorized_cost_cny",
    "posts_allowed",
    "provider_requests",
    "grants_rights",
    "grants_qualification",
    "grants_execution_authority",
    "eligible_for_asset_promotion",
    "replaces_rights_manifest",
    "usage_restriction",
)

_EXPLICIT_FIELD_NAMES: dict[type[BaseModel], tuple[str, ...]] = {
    GeneratedReferenceRightsManifestEvidenceReferenceV1: (
        "ordinal",
        "category",
        "record_id",
        "document_profile",
        "document_sha256",
        "document_size_bytes",
        "media_type",
        "observed_at",
        "effective_from",
        "effective_until",
        "evidence_valid_until",
    ),
    GeneratedReferenceRightsManifestGateResultV1: (
        "ordinal",
        "gate",
        "result",
        "evidence_record_ids",
        "basis",
    ),
    GeneratedReferenceRightsScopeProposalV1: (
        "territory_scope",
        "allowed_use_scope",
        "proposed_scope_valid_until",
    ),
    GeneratedReferenceReviewedRightsScopeV1: (
        "territory_scope",
        "allowed_use_scope",
        "reviewed_scope_valid_until",
        "output_copyright_and_commercial_scope_basis",
        "likeness_privacy_and_sensitive_data_basis",
        "brand_and_protected_content_basis",
        "retention_and_deletion_basis",
        "training_use_prohibition_basis",
        "review_basis",
    ),
    GeneratedReferenceCurrentStatusSubjectClosureV1: (
        "closure_profile",
        "closure_id",
        "closure_sha256",
        "policy_id",
        "policy_version",
        "policy_document_sha256",
        "reference_prompt_artifact_sha256",
        "provider_attempt_outcome_id",
        "provider_attempt_outcome_sha256",
        "candidate_id",
        "candidate_sha256",
        "qualification_request_id",
        "qualification_request_sha256",
        "qualification_decision_id",
        "qualification_decision_sha256",
        "manifest_id",
        "manifest_sha256",
        "subject_id",
        "asset_purpose",
        "media_content_sha256",
        "manifest_at",
        "manifest_valid_until",
    ),
    GeneratedReferenceCurrentStatusObservationRefV1: (
        "ordinal",
        "observation_id",
        "observation_sha256",
        "category",
        "source_identity_ref_sha256",
        "chain_scope_sha256",
        "chain_sha256",
        "valid_from",
        "valid_until",
    ),
    GeneratedReferenceCurrentStatusChainHeadRefV1: (
        "observation_id",
        "observation_sha256",
        "chain_sha256",
    ),
    GeneratedReferenceCurrentStatusChainLinkV1: (
        "link_kind",
        "chain_scope_sha256",
        "predecessor_heads",
    ),
    GeneratedReferenceCurrentStatusCategoryResultV1: (
        "ordinal",
        "category",
        "claim_value",
        "deterministic_effect",
        "category_observation_refs",
        "relied_on_observation_refs",
        "result_valid_until",
    ),
    CreativeSampleGeneratedReferenceRightsManifestV1: _ZERO_AUTHORITY_FIELD_NAMES
    + (
        "schema_version",
        "document_type",
        "manifest_scope",
        "manifest_id",
        "manifest_sha256",
        "policy_id",
        "policy_version",
        "policy_document_sha256",
        "manifest_review_payload_sha256",
        "reference_prompt_artifact_sha256",
        "provider_attempt_outcome_id",
        "provider_attempt_outcome_sha256",
        "candidate_id",
        "candidate_sha256",
        "qualification_request_id",
        "qualification_request_sha256",
        "qualification_decision_id",
        "qualification_decision_sha256",
        "subject_id",
        "asset_purpose",
        "profile_id",
        "profile_version",
        "profile_sha256",
        "catalog_version",
        "catalog_sha256",
        "render_input_sha256",
        "prompt_sha256",
        "prompt_size_bytes",
        "prompt_render_receipt_sha256",
        "media_content_sha256",
        "media_size_bytes",
        "media_technical_record_sha256",
        "provider",
        "model",
        "provider_region",
        "provider_terms_snapshot_id",
        "provider_terms_snapshot_sha256",
        "submitted_at",
        "qualification_decision_at",
        "qualification_valid_until",
        "manifest_at",
        "manifest_valid_until",
        "review_evidence_refs",
        "gate_results",
        "proposed_rights_scope",
        "reviewed_rights_scope",
        "maker_identity_ref_sha256",
        "maker_action_sha256",
        "maker_prepared_at",
        "checker_identity_ref_sha256",
        "checker_action_sha256",
        "checker_reviewed_at",
        "rights_review_performed",
        "eligible_for_separate_generated_current_status_review",
        "current_status_assessment_embedded",
        "status",
        "evidence_scope",
    ),
    CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1: _ZERO_AUTHORITY_FIELD_NAMES
    + (
        "schema_version",
        "document_type",
        "observation_scope",
        "observation_profile",
        "observation_id",
        "observation_sha256",
        "policy_id",
        "policy_version",
        "policy_document_sha256",
        "subject_closure",
        "category",
        "claim_value",
        "source_kind",
        "basis_code",
        "basis_note",
        "source_identity_ref_sha256",
        "source_object_ref",
        "source_object_sha256",
        "source_object_size_bytes",
        "source_object_media_type",
        "source_event_at",
        "observed_at",
        "valid_from",
        "valid_until",
        "chain_link",
        "limitation_codes",
        "status",
        "evidence_scope",
    ),
    CreativeSampleGeneratedReferenceCurrentStatusRequestV1: _ZERO_AUTHORITY_FIELD_NAMES
    + (
        "schema_version",
        "document_type",
        "request_scope",
        "request_id",
        "request_sha256",
        "policy_id",
        "policy_version",
        "policy_document_sha256",
        "subject_closure",
        "status_preparer_identity_ref_sha256",
        "status_preparer_action_sha256",
        "requested_at",
        "request_valid_until",
        "observation_refs",
        "request_basis",
        "status",
        "evidence_scope",
    ),
    CreativeSampleGeneratedReferenceCurrentStatusInstructionV1: _ZERO_AUTHORITY_FIELD_NAMES
    + (
        "schema_version",
        "document_type",
        "instruction_scope",
        "instruction_id",
        "instruction_sha256",
        "policy_id",
        "policy_version",
        "policy_document_sha256",
        "request_id",
        "request_sha256",
        "subject_closure",
        "status_preparer_identity_ref_sha256",
        "status_preparer_action_sha256",
        "status_checker_identity_ref_sha256",
        "status_checker_action_sha256",
        "requested_at",
        "request_valid_until",
        "evaluated_at",
        "category_results",
        "checker_basis",
        "status",
        "evidence_scope",
    ),
    CreativeSampleGeneratedReferenceCurrentStatusDecisionV1: _ZERO_AUTHORITY_FIELD_NAMES
    + (
        "schema_version",
        "document_type",
        "decision_scope",
        "decision_id",
        "decision_sha256",
        "policy_id",
        "policy_version",
        "policy_document_sha256",
        "request_id",
        "request_sha256",
        "instruction_id",
        "instruction_sha256",
        "subject_closure",
        "evaluated_at",
        "decision_at",
        "status_valid_until",
        "category_results",
        "revoked_categories",
        "held_categories",
        "indeterminate_categories",
        "recorded_status",
        "status",
        "evidence_scope",
    ),
    CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1: _ZERO_AUTHORITY_FIELD_NAMES
    + (
        "schema_version",
        "document_type",
        "record_scope",
        "record_id",
        "record_sha256",
        "policy_id",
        "policy_version",
        "policy_document_sha256",
        "subject_closure",
        "request",
        "instruction",
        "decision",
        "status",
        "evidence_scope",
    ),
    CreativeSampleGeneratedReferenceCurrentStatusRecordAsOfAssessmentReceiptV1: (
        _ZERO_AUTHORITY_FIELD_NAMES
    )
    + (
        "schema_version",
        "document_type",
        "receipt_scope",
        "receipt_id",
        "receipt_sha256",
        "policy_id",
        "policy_version",
        "policy_document_sha256",
        "record_id",
        "record_sha256",
        "request_id",
        "request_sha256",
        "decision_id",
        "decision_sha256",
        "subject_closure",
        "explicit_chain_set_sha256",
        "coverage_set_sha256",
        "joint_replay_sha256",
        "as_of_assessment_sha256",
        "as_of",
        "evaluated_at",
        "status_valid_until",
        "window_semantics",
        "recorded_status",
        "as_of_status",
        "recorded_revoked_categories",
        "recorded_held_categories",
        "recorded_indeterminate_categories",
        "record_replay_consistent",
        "same_call_assessment_verified",
        "historical_assessment_only",
        "present_currentness_asserted",
        "limitation_codes",
        "status",
        "evidence_scope",
    ),
}


def _explicit_value(value: object) -> object:
    if isinstance(value, BaseModel):
        if type(value) not in _EXPLICIT_FIELD_NAMES:
            _invalid(f"unregistered explicit projection type: {type(value).__name__}")
        return {
            field_name: _explicit_value(getattr(value, field_name))
            for field_name in _EXPLICIT_FIELD_NAMES[type(value)]
        }
    if type(value) is tuple:
        return [_explicit_value(item) for item in cast(tuple[object, ...], value)]
    if type(value) is list:
        return [_explicit_value(item) for item in cast(list[object], value)]
    if type(value) is dict:
        return {key: _explicit_value(item) for key, item in cast(dict[str, object], value).items()}
    if value is None or type(value) in {str, int, bool}:
        return value
    _invalid(f"value of type {type(value).__name__} has no explicit projection")


_RETAINED_RAW_ANCHOR_FIELDS = frozenset(
    {
        "document_sha256",
        "evidence_preparer_ref_sha256",
        "evidence_preparer_record_sha256",
        "qualifier_ref_sha256",
        "qualifier_record_sha256",
        "provider_terms_snapshot_sha256",
        "attempt_provenance_record_sha256",
        "terminal_observation_record_sha256",
        "maker_identity_ref_sha256",
        "maker_action_sha256",
        "checker_identity_ref_sha256",
        "checker_action_sha256",
        "source_identity_ref_sha256",
        "source_object_sha256",
        "status_preparer_identity_ref_sha256",
        "status_preparer_action_sha256",
        "status_checker_identity_ref_sha256",
        "status_checker_action_sha256",
    }
)


def _collect_sha256_strings(value: object) -> set[str]:
    """Collect semantic/policy/Prompt/media digests, excluding intentional raw anchors."""

    if isinstance(value, BaseModel):
        value = _explicit_value(value)
    result: set[str] = set()
    if type(value) is dict:
        for name, item in cast(dict[str, object], value).items():
            if name in _RETAINED_RAW_ANCHOR_FIELDS:
                continue
            result.update(_collect_sha256_strings(item))
    elif type(value) in {list, tuple}:
        for item in cast(list[object] | tuple[object, ...], value):
            result.update(_collect_sha256_strings(item))
    elif type(value) is str and re.fullmatch(_LOWER_SHA256_PATTERN, value) is not None:
        result.add(value)
    return result


def _reject_retained_digest_aliases(
    retained_digests: tuple[str, ...], *, forbidden: set[str], field: str
) -> None:
    if len(retained_digests) != len(set(retained_digests)):
        _invalid(f"{field} retained raw digests must be pairwise distinct")
    if set(retained_digests) & forbidden:
        _invalid(f"{field} retained raw digest aliases a formal/policy/Prompt/media digest")


_SELF_FIELDS: dict[type[BaseModel], tuple[str, str]] = {
    CreativeSampleGeneratedReferenceRightsManifestV1: ("manifest_id", "manifest_sha256"),
    GeneratedReferenceCurrentStatusSubjectClosureV1: ("closure_id", "closure_sha256"),
    CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1: (
        "observation_id",
        "observation_sha256",
    ),
    CreativeSampleGeneratedReferenceCurrentStatusRequestV1: ("request_id", "request_sha256"),
    CreativeSampleGeneratedReferenceCurrentStatusInstructionV1: (
        "instruction_id",
        "instruction_sha256",
    ),
    CreativeSampleGeneratedReferenceCurrentStatusDecisionV1: ("decision_id", "decision_sha256"),
    CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1: ("record_id", "record_sha256"),
    CreativeSampleGeneratedReferenceCurrentStatusRecordAsOfAssessmentReceiptV1: (
        "receipt_id",
        "receipt_sha256",
    ),
}


def _semantic_projection(model: BaseModel) -> dict[str, object]:
    if type(model) not in _SELF_FIELDS:
        _invalid(f"{type(model).__name__} is not a semantic identity model")
    value = cast(dict[str, object], _explicit_value(model))
    id_field, sha_field = _SELF_FIELDS[type(model)]
    return {key: item for key, item in value.items() if key not in {id_field, sha_field}}


def _validate_identity(
    model: BaseModel,
    *,
    id_field: str,
    sha_field: str,
    stem: str,
    domain: bytes,
) -> None:
    expected_sha = _semantic_sha256(domain, _semantic_projection(model))
    if getattr(model, sha_field) != expected_sha:
        _invalid(f"{sha_field} does not bind the exact explicit projection")
    if getattr(model, id_field) != f"{stem}{expected_sha[:20]}":
        _invalid(f"{id_field} does not agree with {sha_field}")


def _observation_ref_key(
    value: GeneratedReferenceCurrentStatusObservationRefV1,
) -> tuple[str, str, str]:
    return (value.observation_id, value.observation_sha256, value.chain_sha256)


def _validate_category_results(
    values: tuple[GeneratedReferenceCurrentStatusCategoryResultV1, ...],
) -> None:
    if tuple(item.category for item in values) != CURRENT_STATUS_CATEGORY_ORDER:
        _invalid("category_results must use exact policy order")
    if tuple(item.ordinal for item in values) != tuple(range(9)):
        _invalid("category_results must use exact zero-based ordinals")


def _derive_effect(
    category: CurrentStatusCategory, claim: CurrentStatusClaimValue
) -> CurrentStatusDeterministicEffect:
    if claim in {"UNKNOWN", "NOT_ASSESSED", "CONFLICT"}:
        return "INDETERMINATE"
    adverse = category in CURRENT_STATUS_ADVERSE_CATEGORY_ORDER
    if adverse:
        return "ADVERSE_PRESENT" if claim == "PRESENT" else "ADVERSE_ABSENT"
    return "POSITIVE_PRESENT" if claim == "PRESENT" else "POSITIVE_ABSENT"


def _derive_status_and_diagnostics(
    category_results: tuple[GeneratedReferenceCurrentStatusCategoryResultV1, ...],
) -> tuple[
    CurrentStatusResult,
    tuple[CurrentStatusCategory, ...],
    tuple[CurrentStatusCategory, ...],
    tuple[CurrentStatusCategory, ...],
]:
    revoked = tuple(
        item.category
        for item in category_results
        if item.category == "REVOCATION_EFFECTIVE"
        and item.deterministic_effect == "ADVERSE_PRESENT"
    )
    held = tuple(
        item.category
        for item in category_results
        if (
            item.category in {"HOLD_ACTIVE", "COMPLAINT_OPEN", "DISPUTE_OPEN"}
            and item.deterministic_effect == "ADVERSE_PRESENT"
        )
        or (
            item.category in CURRENT_STATUS_POSITIVE_CATEGORY_ORDER
            and item.deterministic_effect == "POSITIVE_ABSENT"
        )
    )
    indeterminate = tuple(
        item.category for item in category_results if item.deterministic_effect == "INDETERMINATE"
    )
    if revoked:
        status: CurrentStatusResult = "REVOKED"
    elif held:
        status = "HELD"
    elif indeterminate:
        status = "INDETERMINATE"
    else:
        status = "CURRENT"
    return status, revoked, held, indeterminate


def _validate_decision_semantics(
    value: CreativeSampleGeneratedReferenceCurrentStatusDecisionV1,
) -> None:
    _validate_category_results(value.category_results)
    if value.evaluated_at != value.decision_at:
        _invalid("evaluated_at must exactly equal decision_at")
    expected_until = min(item.result_valid_until for item in value.category_results)
    if value.status_valid_until != expected_until:
        _invalid("status_valid_until must be the exact earliest category expiry")
    expected_status, revoked, held, indeterminate = _derive_status_and_diagnostics(
        value.category_results
    )
    if (
        value.recorded_status,
        value.revoked_categories,
        value.held_categories,
        value.indeterminate_categories,
    ) != (expected_status, revoked, held, indeterminate):
        _invalid("Decision diagnostics or recorded_status drift from frozen resolver")


def _validate_request_refs(value: CreativeSampleGeneratedReferenceCurrentStatusRequestV1) -> None:
    keys = tuple(_observation_ref_key(item) for item in value.observation_refs)
    if len(keys) != len(set(keys)):
        _invalid("Request observation_refs must be unique")
    category_index = {
        category: index for index, category in enumerate(CURRENT_STATUS_CATEGORY_ORDER)
    }
    expected = tuple(
        sorted(
            value.observation_refs,
            key=lambda item: (category_index[item.category], item.valid_from, item.observation_id),
        )
    )
    if value.observation_refs != expected:
        _invalid("Request observation_refs are not in canonical policy order")
    if set(item.category for item in value.observation_refs) != set(CURRENT_STATUS_CATEGORY_ORDER):
        _invalid("Request must contain at least one target for every category")
    if tuple(item.ordinal for item in value.observation_refs) != tuple(
        range(len(value.observation_refs))
    ):
        _invalid("Request observation_refs must use zero-based Request ordinals")
    requested_at = _parse_utc(value.requested_at, field="requested_at")
    expected_until = min(
        requested_at + timedelta(seconds=86_400),
        _parse_utc(value.subject_closure.manifest_valid_until, field="manifest_valid_until"),
    )
    if value.request_valid_until != expected_until.strftime("%Y-%m-%dT%H:%M:%SZ"):
        _invalid("request_valid_until is not uniquely derived")


_BASIS_MATRIX: dict[CurrentStatusCategory, dict[str, frozenset[str]]] = {
    cast(CurrentStatusCategory, item["category"]): {
        "PRESENT": frozenset(cast(list[str], item["present_basis_codes"])),
        "ABSENT_WITH_EVIDENCE": frozenset(cast(list[str], item["absent_basis_codes"])),
    }
    for item in cast(
        list[dict[str, object]], json.loads(_CURRENT_STATUS_POLICY_JSON)["basis_claim_matrix"]
    )
}
_SOURCE_APPLICABILITY: dict[tuple[CurrentStatusCategory, str], frozenset[str]] = {}
_CATEGORY_SOURCE_KINDS_MUTABLE: dict[CurrentStatusCategory, set[str]] = {
    category: set() for category in CURRENT_STATUS_CATEGORY_ORDER
}
for _entry in cast(
    list[dict[str, object]], json.loads(_CURRENT_STATUS_POLICY_JSON)["source_kind_applicability"]
):
    for _basis in cast(list[str], _entry["basis_codes"]):
        _SOURCE_APPLICABILITY[(cast(CurrentStatusCategory, _entry["category"]), _basis)] = (
            frozenset(cast(list[str], _entry["source_kinds"]))
        )
    _CATEGORY_SOURCE_KINDS_MUTABLE[cast(CurrentStatusCategory, _entry["category"])].update(
        cast(list[str], _entry["source_kinds"])
    )
_CATEGORY_SOURCE_KINDS = {
    category: frozenset(values) for category, values in _CATEGORY_SOURCE_KINDS_MUTABLE.items()
}


def _validate_observation_semantics(
    value: CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1,
) -> None:
    if value.limitation_codes != CURRENT_STATUS_LIMITATION_CODE_ORDER:
        _invalid("Observation limitation_codes must use exact frozen order")
    source_event = _parse_utc(value.source_event_at, field="source_event_at")
    observed = _parse_utc(value.observed_at, field="observed_at")
    valid_from = _parse_utc(value.valid_from, field="valid_from")
    valid_until = _parse_utc(value.valid_until, field="valid_until")
    if source_event > observed or max(observed, valid_from) >= valid_until:
        _invalid("Observation temporal window is invalid")
    if value.valid_until > value.subject_closure.manifest_valid_until:
        _invalid("Observation cannot outlive the Rights Manifest")
    if value.claim_value in {"PRESENT", "ABSENT_WITH_EVIDENCE"}:
        if value.basis_code not in _BASIS_MATRIX[value.category][value.claim_value]:
            _invalid("basis_code is incompatible with category and claim_value")
    elif value.basis_code not in {
        "INITIAL_STATUS_UNKNOWN",
        "INITIAL_STATUS_NOT_ASSESSED",
        "STATUS_RECONFIRMED",
        "STATUS_BECAME_UNKNOWN",
        "CONFLICT_IDENTIFIED",
        "CONFLICT_RECONCILED",
    }:
        _invalid("non-terminal claim requires a generic basis code")
    applicable = _SOURCE_APPLICABILITY.get((value.category, value.basis_code))
    if applicable is not None and value.source_kind not in applicable:
        _invalid("source_kind is incompatible with category and basis_code")
    if value.source_kind not in _CATEGORY_SOURCE_KINDS[value.category]:
        _invalid("source_kind is not applicable to this category")
    expected_scope = generated_reference_current_status_chain_scope_sha256(
        value.subject_closure,
        category=value.category,
        source_identity_ref_sha256=value.source_identity_ref_sha256,
        source_kind=value.source_kind,
        observation_profile=value.observation_profile,
    )
    if value.chain_link.chain_scope_sha256 != expected_scope:
        _invalid("chain_link.chain_scope_sha256 does not bind the exact chain scope")


def _validate_record_closure(
    value: CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1,
) -> None:
    request, instruction, decision = value.request, value.instruction, value.decision
    if (
        request.subject_closure != value.subject_closure
        or instruction.subject_closure != value.subject_closure
        or decision.subject_closure != value.subject_closure
    ):
        _invalid("Record subject closure is not identical across embedded documents")
    if (instruction.request_id, instruction.request_sha256) != (
        request.request_id,
        request.request_sha256,
    ):
        _invalid("Instruction does not bind embedded Request")
    if (decision.request_id, decision.request_sha256) != (
        request.request_id,
        request.request_sha256,
    ):
        _invalid("Decision does not bind embedded Request")
    if (decision.instruction_id, decision.instruction_sha256) != (
        instruction.instruction_id,
        instruction.instruction_sha256,
    ):
        _invalid("Decision does not bind embedded Instruction")
    if instruction.category_results != decision.category_results:
        _invalid("Decision category_results do not equal Instruction results")


_MANIFEST_POLICY_PROJECTION = cast(
    dict[str, object], json.loads(_MANIFEST_POLICY_JSON, object_pairs_hook=_json_no_duplicates)
)
_CURRENT_STATUS_POLICY_PROJECTION = cast(
    dict[str, object],
    json.loads(_CURRENT_STATUS_POLICY_JSON, object_pairs_hook=_json_no_duplicates),
)
if (
    len(_MANIFEST_POLICY_JSON.encode("utf-8")) != 4_686
    or _raw_sha256(_MANIFEST_POLICY_JSON.encode("utf-8"))
    != GENERATED_REFERENCE_RIGHTS_MANIFEST_POLICY_DOCUMENT_SHA256
):
    raise RuntimeError("frozen generated-reference Rights Manifest policy drift")
if (
    len(_CURRENT_STATUS_POLICY_JSON.encode("utf-8")) != 14_138
    or _raw_sha256(_CURRENT_STATUS_POLICY_JSON.encode("utf-8"))
    != GENERATED_REFERENCE_CURRENT_STATUS_POLICY_DOCUMENT_SHA256
):
    raise RuntimeError("frozen generated-reference current-status policy drift")
if _compact_json(_MANIFEST_POLICY_PROJECTION) != _MANIFEST_POLICY_JSON.encode(
    "utf-8"
) or _compact_json(_CURRENT_STATUS_POLICY_PROJECTION) != _CURRENT_STATUS_POLICY_JSON.encode(
    "utf-8"
):
    raise RuntimeError("frozen policy compact canonical bytes drift")


def generated_reference_rights_manifest_policy_projection() -> dict[str, object]:
    return cast(dict[str, object], json.loads(_MANIFEST_POLICY_JSON))


def generated_reference_current_status_policy_projection() -> dict[str, object]:
    return cast(dict[str, object], json.loads(_CURRENT_STATUS_POLICY_JSON))


def _exact_model(model: BaseModel, expected: type[BaseModel], *, field: str) -> BaseModel:
    if type(model) is not expected:
        _invalid(f"{field} must be exact {expected.__name__}")
    return expected.model_validate(model)


def _public_projection(model: BaseModel, expected: type[BaseModel]) -> dict[str, object]:
    validated = _exact_model(model, expected, field=expected.__name__)
    return _semantic_projection(validated)


def generated_reference_current_status_subject_closure_projection(
    value: GeneratedReferenceCurrentStatusSubjectClosureV1,
) -> dict[str, object]:
    return _public_projection(value, GeneratedReferenceCurrentStatusSubjectClosureV1)


def generated_reference_current_status_subject_closure_sha256(
    value: GeneratedReferenceCurrentStatusSubjectClosureV1,
) -> str:
    return _semantic_sha256(
        GENERATED_REFERENCE_CURRENT_STATUS_SUBJECT_CLOSURE_SHA256_DOMAIN,
        generated_reference_current_status_subject_closure_projection(value),
    )


def generated_reference_rights_manifest_review_payload_projection(
    value: CreativeSampleGeneratedReferenceRightsManifestV1,
) -> dict[str, object]:
    if type(value) is not CreativeSampleGeneratedReferenceRightsManifestV1:
        _invalid("Manifest must have its exact public Contract type")
    return {
        "manifest_review_payload_profile": (
            "sdc.generated-reference-rights-manifest-review-payload.v1"
        ),
        "manifest_policy_id": value.policy_id,
        "manifest_policy_version": value.policy_version,
        "manifest_policy_document_sha256": value.policy_document_sha256,
        "reference_prompt_artifact_sha256": value.reference_prompt_artifact_sha256,
        "provider_attempt_outcome_id": value.provider_attempt_outcome_id,
        "provider_attempt_outcome_sha256": value.provider_attempt_outcome_sha256,
        "candidate_id": value.candidate_id,
        "candidate_sha256": value.candidate_sha256,
        "qualification_request_id": value.qualification_request_id,
        "qualification_request_sha256": value.qualification_request_sha256,
        "qualification_decision_id": value.qualification_decision_id,
        "qualification_decision_sha256": value.qualification_decision_sha256,
        "subject_id": value.subject_id,
        "asset_purpose": value.asset_purpose,
        "profile_id": value.profile_id,
        "profile_version": value.profile_version,
        "profile_sha256": value.profile_sha256,
        "catalog_version": value.catalog_version,
        "catalog_sha256": value.catalog_sha256,
        "render_input_sha256": value.render_input_sha256,
        "prompt_sha256": value.prompt_sha256,
        "prompt_size_bytes": value.prompt_size_bytes,
        "prompt_render_receipt_sha256": value.prompt_render_receipt_sha256,
        "media_content_sha256": value.media_content_sha256,
        "media_size_bytes": value.media_size_bytes,
        "media_technical_record_sha256": value.media_technical_record_sha256,
        "provider": value.provider,
        "model": value.model,
        "provider_region": value.provider_region,
        "provider_terms_snapshot_id": value.provider_terms_snapshot_id,
        "provider_terms_snapshot_sha256": value.provider_terms_snapshot_sha256,
        "submitted_at": value.submitted_at,
        "qualification_decision_at": value.qualification_decision_at,
        "qualification_valid_until": value.qualification_valid_until,
        "manifest_at": value.manifest_at,
        "review_evidence_refs": _explicit_value(value.review_evidence_refs),
        "proposed_rights_scope": _explicit_value(value.proposed_rights_scope),
        "evidence_scope": "EXPLICIT_FINITE_BOUND_SET_ONLY",
    }


def generated_reference_rights_manifest_review_payload_sha256(
    value: CreativeSampleGeneratedReferenceRightsManifestV1,
) -> str:
    return _semantic_sha256(
        GENERATED_REFERENCE_RIGHTS_MANIFEST_REVIEW_PAYLOAD_SHA256_DOMAIN,
        generated_reference_rights_manifest_review_payload_projection(value),
    )


def creative_sample_generated_reference_rights_manifest_projection(
    value: CreativeSampleGeneratedReferenceRightsManifestV1,
) -> dict[str, object]:
    return _public_projection(value, CreativeSampleGeneratedReferenceRightsManifestV1)


def creative_sample_generated_reference_rights_manifest_sha256(
    value: CreativeSampleGeneratedReferenceRightsManifestV1,
) -> str:
    return _semantic_sha256(
        GENERATED_REFERENCE_RIGHTS_MANIFEST_SHA256_DOMAIN,
        creative_sample_generated_reference_rights_manifest_projection(value),
    )


def creative_sample_generated_reference_current_status_source_observation_projection(
    value: CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1,
) -> dict[str, object]:
    return _public_projection(
        value, CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1
    )


def creative_sample_generated_reference_current_status_source_observation_sha256(
    value: CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1,
) -> str:
    return _semantic_sha256(
        GENERATED_REFERENCE_CURRENT_STATUS_SOURCE_OBSERVATION_SHA256_DOMAIN,
        creative_sample_generated_reference_current_status_source_observation_projection(value),
    )


def creative_sample_generated_reference_current_status_request_projection(
    value: CreativeSampleGeneratedReferenceCurrentStatusRequestV1,
) -> dict[str, object]:
    return _public_projection(value, CreativeSampleGeneratedReferenceCurrentStatusRequestV1)


def creative_sample_generated_reference_current_status_request_sha256(
    value: CreativeSampleGeneratedReferenceCurrentStatusRequestV1,
) -> str:
    return _semantic_sha256(
        GENERATED_REFERENCE_CURRENT_STATUS_REQUEST_SHA256_DOMAIN,
        creative_sample_generated_reference_current_status_request_projection(value),
    )


def creative_sample_generated_reference_current_status_instruction_projection(
    value: CreativeSampleGeneratedReferenceCurrentStatusInstructionV1,
) -> dict[str, object]:
    return _public_projection(value, CreativeSampleGeneratedReferenceCurrentStatusInstructionV1)


def creative_sample_generated_reference_current_status_instruction_sha256(
    value: CreativeSampleGeneratedReferenceCurrentStatusInstructionV1,
) -> str:
    return _semantic_sha256(
        GENERATED_REFERENCE_CURRENT_STATUS_INSTRUCTION_SHA256_DOMAIN,
        creative_sample_generated_reference_current_status_instruction_projection(value),
    )


def creative_sample_generated_reference_current_status_decision_projection(
    value: CreativeSampleGeneratedReferenceCurrentStatusDecisionV1,
) -> dict[str, object]:
    return _public_projection(value, CreativeSampleGeneratedReferenceCurrentStatusDecisionV1)


def creative_sample_generated_reference_current_status_decision_sha256(
    value: CreativeSampleGeneratedReferenceCurrentStatusDecisionV1,
) -> str:
    return _semantic_sha256(
        GENERATED_REFERENCE_CURRENT_STATUS_DECISION_SHA256_DOMAIN,
        creative_sample_generated_reference_current_status_decision_projection(value),
    )


def creative_sample_generated_reference_current_status_evidence_record_projection(
    value: CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1,
) -> dict[str, object]:
    return _public_projection(value, CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1)


def creative_sample_generated_reference_current_status_evidence_record_sha256(
    value: CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1,
) -> str:
    return _semantic_sha256(
        GENERATED_REFERENCE_CURRENT_STATUS_EVIDENCE_RECORD_SHA256_DOMAIN,
        creative_sample_generated_reference_current_status_evidence_record_projection(value),
    )


def creative_sample_generated_reference_current_status_record_as_of_assessment_receipt_projection(
    value: CreativeSampleGeneratedReferenceCurrentStatusRecordAsOfAssessmentReceiptV1,
) -> dict[str, object]:
    return _public_projection(
        value,
        CreativeSampleGeneratedReferenceCurrentStatusRecordAsOfAssessmentReceiptV1,
    )


def creative_sample_generated_reference_current_status_record_as_of_assessment_receipt_sha256(
    value: CreativeSampleGeneratedReferenceCurrentStatusRecordAsOfAssessmentReceiptV1,
) -> str:
    return _semantic_sha256(
        GENERATED_REFERENCE_CURRENT_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_SHA256_DOMAIN,
        creative_sample_generated_reference_current_status_record_as_of_assessment_receipt_projection(
            value
        ),
    )


def generated_reference_contract_document_bytes(value: BaseModel) -> bytes:
    if type(value) not in _SELF_FIELDS:
        _invalid("only one exact ADR-044 formal Contract is admitted")
    validated = _exact_model(value, type(value), field="Contract")
    return _formal_json(_explicit_value(validated))


def _build_identity_contract(
    model_type: type[BaseModel],
    *,
    values: Mapping[str, object],
    id_field: str,
    sha_field: str,
    stem: str,
    domain: bytes,
) -> BaseModel:
    payload = dict(values)
    if id_field in payload or sha_field in payload:
        _invalid(f"{id_field} and {sha_field} are compiler-derived")
    explicit_fields = _EXPLICIT_FIELD_NAMES[model_type]
    projection = {
        key: _explicit_value(payload[key])
        for key in explicit_fields
        if key not in {id_field, sha_field}
    }
    extra = set(payload) - (set(explicit_fields) - {id_field, sha_field})
    missing = (set(explicit_fields) - {id_field, sha_field}) - set(payload)
    if extra or missing:
        _invalid(
            "Contract inputs differ from the closed projection; "
            f"missing={sorted(missing)}, extra={sorted(extra)}"
        )
    digest = _semantic_sha256(domain, projection)
    payload[id_field] = f"{stem}{digest[:20]}"
    payload[sha_field] = digest
    return model_type.model_validate(payload)


def _base_current_values() -> dict[str, object]:
    return {
        "schema_version": _SCHEMA_VERSION,
        "policy_id": GENERATED_REFERENCE_CURRENT_STATUS_POLICY_ID,
        "policy_version": GENERATED_REFERENCE_CURRENT_STATUS_POLICY_VERSION,
        "policy_document_sha256": GENERATED_REFERENCE_CURRENT_STATUS_POLICY_DOCUMENT_SHA256,
        "evidence_scope": "EXPLICIT_FINITE_BOUND_SET_ONLY",
        **_zero_authority_values(),
    }


def build_generated_reference_current_status_subject_closure(
    manifest: CreativeSampleGeneratedReferenceRightsManifestV1,
) -> GeneratedReferenceCurrentStatusSubjectClosureV1:
    try:
        validated = cast(
            CreativeSampleGeneratedReferenceRightsManifestV1,
            _exact_model(
                manifest, CreativeSampleGeneratedReferenceRightsManifestV1, field="manifest"
            ),
        )
        values: dict[str, object] = {
            "closure_profile": "sdc.generated-reference-current-status-subject-closure.v1",
            "policy_id": GENERATED_REFERENCE_CURRENT_STATUS_POLICY_ID,
            "policy_version": GENERATED_REFERENCE_CURRENT_STATUS_POLICY_VERSION,
            "policy_document_sha256": GENERATED_REFERENCE_CURRENT_STATUS_POLICY_DOCUMENT_SHA256,
            "reference_prompt_artifact_sha256": validated.reference_prompt_artifact_sha256,
            "provider_attempt_outcome_id": validated.provider_attempt_outcome_id,
            "provider_attempt_outcome_sha256": validated.provider_attempt_outcome_sha256,
            "candidate_id": validated.candidate_id,
            "candidate_sha256": validated.candidate_sha256,
            "qualification_request_id": validated.qualification_request_id,
            "qualification_request_sha256": validated.qualification_request_sha256,
            "qualification_decision_id": validated.qualification_decision_id,
            "qualification_decision_sha256": validated.qualification_decision_sha256,
            "manifest_id": validated.manifest_id,
            "manifest_sha256": validated.manifest_sha256,
            "subject_id": validated.subject_id,
            "asset_purpose": validated.asset_purpose,
            "media_content_sha256": validated.media_content_sha256,
            "manifest_at": validated.manifest_at,
            "manifest_valid_until": validated.manifest_valid_until,
        }
        return cast(
            GeneratedReferenceCurrentStatusSubjectClosureV1,
            _build_identity_contract(
                GeneratedReferenceCurrentStatusSubjectClosureV1,
                values=values,
                id_field="closure_id",
                sha_field="closure_sha256",
                stem="generated_reference_current_status_subject_closure_v1_",
                domain=GENERATED_REFERENCE_CURRENT_STATUS_SUBJECT_CLOSURE_SHA256_DOMAIN,
            ),
        )
    except (TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceRightsCurrentStatusError(
            "SUBJECT_CLOSURE_CONTRACT_INVALID", "subject closure construction failed"
        ) from exc


def generated_reference_current_status_chain_scope_projection(
    subject_closure: GeneratedReferenceCurrentStatusSubjectClosureV1,
    *,
    category: CurrentStatusCategory,
    source_identity_ref_sha256: str,
    source_kind: CurrentStatusSourceKind,
    observation_profile: str = "sdc.generated-reference-current-status-observation-profile.v1",
) -> dict[str, object]:
    closure = cast(
        GeneratedReferenceCurrentStatusSubjectClosureV1,
        _exact_model(
            subject_closure,
            GeneratedReferenceCurrentStatusSubjectClosureV1,
            field="subject_closure",
        ),
    )
    if category not in CURRENT_STATUS_CATEGORY_ORDER:
        _invalid("unknown current-status category")
    source_kind_order = cast(list[str], _CURRENT_STATUS_POLICY_PROJECTION["source_kind_order"])
    if source_kind not in source_kind_order:
        _invalid("unknown current-status source kind")
    if re.fullmatch(_LOWER_SHA256_PATTERN, source_identity_ref_sha256) is None:
        _invalid("source_identity_ref_sha256 is invalid")
    if observation_profile != "sdc.generated-reference-current-status-observation-profile.v1":
        _invalid("observation_profile drift")
    return {
        "subject_closure_id": closure.closure_id,
        "subject_closure_sha256": closure.closure_sha256,
        "category": category,
        "source_identity_ref_sha256": source_identity_ref_sha256,
        "source_kind": source_kind,
        "observation_profile": observation_profile,
        "policy_version": GENERATED_REFERENCE_CURRENT_STATUS_POLICY_VERSION,
    }


def generated_reference_current_status_chain_scope_sha256(
    subject_closure: GeneratedReferenceCurrentStatusSubjectClosureV1,
    *,
    category: CurrentStatusCategory,
    source_identity_ref_sha256: str,
    source_kind: CurrentStatusSourceKind,
    observation_profile: str = "sdc.generated-reference-current-status-observation-profile.v1",
) -> str:
    return _semantic_sha256(
        GENERATED_REFERENCE_CURRENT_STATUS_CHAIN_SCOPE_SHA256_DOMAIN,
        generated_reference_current_status_chain_scope_projection(
            subject_closure,
            category=category,
            source_identity_ref_sha256=source_identity_ref_sha256,
            source_kind=source_kind,
            observation_profile=observation_profile,
        ),
    )


def generated_reference_current_status_chain_projection(
    observation: CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1,
) -> dict[str, object]:
    validated = cast(
        CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1,
        _exact_model(
            observation,
            CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1,
            field="observation",
        ),
    )
    return {
        "chain_scope_sha256": validated.chain_link.chain_scope_sha256,
        "observation_id": validated.observation_id,
        "observation_sha256": validated.observation_sha256,
        "link_kind": validated.chain_link.link_kind,
        "predecessor_heads": _explicit_value(validated.chain_link.predecessor_heads),
    }


def generated_reference_current_status_chain_sha256(
    observation: CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1,
) -> str:
    return _semantic_sha256(
        GENERATED_REFERENCE_CURRENT_STATUS_CHAIN_SHA256_DOMAIN,
        generated_reference_current_status_chain_projection(observation),
    )


def generated_reference_current_status_observation_ref(
    observation: CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1,
    *,
    ordinal: int,
) -> GeneratedReferenceCurrentStatusObservationRefV1:
    validated = cast(
        CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1,
        _exact_model(
            observation,
            CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1,
            field="observation",
        ),
    )
    return GeneratedReferenceCurrentStatusObservationRefV1.model_validate(
        {
            "ordinal": ordinal,
            "observation_id": validated.observation_id,
            "observation_sha256": validated.observation_sha256,
            "category": validated.category,
            "source_identity_ref_sha256": validated.source_identity_ref_sha256,
            "chain_scope_sha256": validated.chain_link.chain_scope_sha256,
            "chain_sha256": generated_reference_current_status_chain_sha256(validated),
            "valid_from": validated.valid_from,
            "valid_until": validated.valid_until,
        }
    )


def build_generated_reference_current_status_source_observation(
    *,
    subject_closure: GeneratedReferenceCurrentStatusSubjectClosureV1,
    category: CurrentStatusCategory,
    claim_value: CurrentStatusClaimValue,
    source_kind: CurrentStatusSourceKind,
    basis_code: CurrentStatusBasisCode,
    basis_note: str,
    source_identity_bytes: bytes,
    source_object_ref: str,
    source_object_bytes: bytes,
    source_object_media_type: str,
    source_event_at: str,
    observed_at: str,
    valid_from: str,
    valid_until: str,
    link_kind: CurrentStatusLinkKind,
    predecessor_heads: tuple[GeneratedReferenceCurrentStatusChainHeadRefV1, ...] = (),
) -> CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1:
    try:
        closure = cast(
            GeneratedReferenceCurrentStatusSubjectClosureV1,
            _exact_model(
                subject_closure,
                GeneratedReferenceCurrentStatusSubjectClosureV1,
                field="subject_closure",
            ),
        )
        if type(source_object_bytes) is not bytes or not 1 <= len(source_object_bytes) <= 262_144:
            _invalid("source_object_bytes must contain 1..262144 exact bytes")
        _source_identity, source_identity_ref_sha256 = _source_reference(
            source_identity_bytes, field="Source Observation identity reference"
        )
        scope_sha = generated_reference_current_status_chain_scope_sha256(
            closure,
            category=category,
            source_identity_ref_sha256=source_identity_ref_sha256,
            source_kind=source_kind,
        )
        values = {
            **_base_current_values(),
            "document_type": (
                "sdc.creative-sample-generated-reference-current-status-source-observation-v1"
            ),
            "observation_scope": "GENERATED_REFERENCE_CURRENT_STATUS_SOURCE_EVIDENCE_ONLY",
            "observation_profile": "sdc.generated-reference-current-status-observation-profile.v1",
            "subject_closure": closure,
            "category": category,
            "claim_value": claim_value,
            "source_kind": source_kind,
            "basis_code": basis_code,
            "basis_note": basis_note,
            "source_identity_ref_sha256": source_identity_ref_sha256,
            "source_object_ref": source_object_ref,
            "source_object_sha256": _raw_sha256(source_object_bytes),
            "source_object_size_bytes": len(source_object_bytes),
            "source_object_media_type": source_object_media_type,
            "source_event_at": source_event_at,
            "observed_at": observed_at,
            "valid_from": valid_from,
            "valid_until": valid_until,
            "chain_link": GeneratedReferenceCurrentStatusChainLinkV1(
                link_kind=link_kind,
                chain_scope_sha256=scope_sha,
                predecessor_heads=predecessor_heads,
            ),
            "limitation_codes": CURRENT_STATUS_LIMITATION_CODE_ORDER,
            "status": "GENERATED_CURRENT_STATUS_SOURCE_OBSERVATION_RECORDED",
        }
        return cast(
            CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1,
            _build_identity_contract(
                CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1,
                values=values,
                id_field="observation_id",
                sha_field="observation_sha256",
                stem="generated_reference_current_status_source_observation_v1_",
                domain=GENERATED_REFERENCE_CURRENT_STATUS_SOURCE_OBSERVATION_SHA256_DOMAIN,
            ),
        )
    except (TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceRightsCurrentStatusError(
            "OBSERVATION_CONTRACT_INVALID", "Source Observation construction failed"
        ) from exc


def _merge_forced(
    supplied: Mapping[str, object], forced: Mapping[str, object]
) -> dict[str, object]:
    result = dict(supplied)
    for key, value in forced.items():
        if key in result and result[key] != value:
            _invalid(f"{key} is frozen and cannot be caller-selected")
        result[key] = value
    return result


def _build_generated_reference_rights_manifest_from_values(
    values: Mapping[str, object] | None = None,
    /,
    **fields: object,
) -> CreativeSampleGeneratedReferenceRightsManifestV1:
    """Build a positive Manifest from a closed, already reviewed field set.

    Retained human identity/action documents remain process-private.  Callers supply only their
    exact raw SHA anchors and the closed review payload digest in ``values``/``fields``.  The
    function fixes every policy, status, authority and self-identity value and admits no negative
    or indeterminate portable Manifest.
    """

    try:
        if values is not None and fields:
            _invalid("use either one values mapping or keyword fields, not both")
        supplied = dict(values) if values is not None else dict(fields)
        forced = {
            "schema_version": _SCHEMA_VERSION,
            "document_type": "sdc.creative-sample-generated-reference-rights-manifest-v1",
            "manifest_scope": "GENERATED_REFERENCE_RIGHTS_REVIEW_ONLY",
            "policy_id": GENERATED_REFERENCE_RIGHTS_MANIFEST_POLICY_ID,
            "policy_version": GENERATED_REFERENCE_RIGHTS_MANIFEST_POLICY_VERSION,
            "policy_document_sha256": GENERATED_REFERENCE_RIGHTS_MANIFEST_POLICY_DOCUMENT_SHA256,
            "rights_review_performed": True,
            "eligible_for_separate_generated_current_status_review": True,
            "current_status_assessment_embedded": False,
            "status": "GENERATED_RIGHTS_MANIFEST_RECORDED",
            "evidence_scope": "EXPLICIT_FINITE_BOUND_SET_ONLY",
            **_zero_authority_values(),
        }
        payload = _merge_forced(supplied, forced)
        try:
            evidence_refs = tuple(
                item
                if type(item) is GeneratedReferenceRightsManifestEvidenceReferenceV1
                else GeneratedReferenceRightsManifestEvidenceReferenceV1.model_validate(item)
                for item in cast(Sequence[object], payload["review_evidence_refs"])
            )
            proposed_scope = (
                payload["proposed_rights_scope"]
                if type(payload["proposed_rights_scope"]) is GeneratedReferenceRightsScopeProposalV1
                else GeneratedReferenceRightsScopeProposalV1.model_validate(
                    payload["proposed_rights_scope"]
                )
            )
            reviewed_scope = (
                payload["reviewed_rights_scope"]
                if type(payload["reviewed_rights_scope"]) is GeneratedReferenceReviewedRightsScopeV1
                else GeneratedReferenceReviewedRightsScopeV1.model_validate(
                    payload["reviewed_rights_scope"]
                )
            )
        except KeyError as exc:
            _invalid(f"missing Manifest review input: {exc.args[0]}")
        payload["review_evidence_refs"] = evidence_refs
        payload["proposed_rights_scope"] = proposed_scope
        payload["reviewed_rights_scope"] = reviewed_scope
        manifest_at = _parse_utc(cast(str, payload["manifest_at"]), field="manifest_at")
        bounds = [manifest_at + timedelta(seconds=86_400)]
        for evidence in evidence_refs[2:]:
            for bound_name, bound in (
                ("effective_until", evidence.effective_until),
                ("evidence_valid_until", evidence.evidence_valid_until),
            ):
                if bound != "PERPETUAL":
                    bounds.append(_parse_utc(bound, field=bound_name))
        bounds.append(
            _parse_utc(
                reviewed_scope.reviewed_scope_valid_until,
                field="reviewed_scope_valid_until",
            )
        )
        derived_until = min(bounds).strftime("%Y-%m-%dT%H:%M:%SZ")
        if "manifest_valid_until" in payload and payload["manifest_valid_until"] != derived_until:
            _invalid("caller-supplied manifest_valid_until differs from frozen derivation")
        payload["manifest_valid_until"] = derived_until
        provisional_values = {
            name: value
            for name, value in payload.items()
            if name not in {"manifest_id", "manifest_sha256", "manifest_review_payload_sha256"}
        }
        provisional = CreativeSampleGeneratedReferenceRightsManifestV1.model_construct(
            **provisional_values,  # type: ignore[arg-type]
            manifest_id="generated_reference_rights_manifest_v1_00000000000000000000",
            manifest_sha256="0" * 64,
            manifest_review_payload_sha256="0" * 64,
        )
        derived_payload_sha = _semantic_sha256(
            GENERATED_REFERENCE_RIGHTS_MANIFEST_REVIEW_PAYLOAD_SHA256_DOMAIN,
            generated_reference_rights_manifest_review_payload_projection(provisional),
        )
        if (
            "manifest_review_payload_sha256" in payload
            and payload["manifest_review_payload_sha256"] != derived_payload_sha
        ):
            _invalid("caller-supplied Manifest review payload digest differs from derivation")
        payload["manifest_review_payload_sha256"] = derived_payload_sha
        return cast(
            CreativeSampleGeneratedReferenceRightsManifestV1,
            _build_identity_contract(
                CreativeSampleGeneratedReferenceRightsManifestV1,
                values=payload,
                id_field="manifest_id",
                sha_field="manifest_sha256",
                stem="generated_reference_rights_manifest_v1_",
                domain=GENERATED_REFERENCE_RIGHTS_MANIFEST_SHA256_DOMAIN,
            ),
        )
    except (TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceRightsCurrentStatusError(
            "MANIFEST_CONTRACT_INVALID", "positive Rights Manifest construction failed"
        ) from exc


def _verify_generated_reference_rights_manifest_anchors(
    manifest: CreativeSampleGeneratedReferenceRightsManifestV1,
    *,
    artifact: CreativeSampleReferenceVisualPromptArtifactV1 | None = None,
    outcome: CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1 | None = None,
    candidate: CreativeSampleGeneratedReferenceCandidateV1 | None = None,
    qualification_request: CreativeSampleGeneratedReferenceCandidateQualificationRequestV1
    | None = None,
    qualification_decision: CreativeSampleGeneratedReferenceCandidateQualificationDecisionV1
    | None = None,
    media_bytes: bytes | None = None,
) -> CreativeSampleGeneratedReferenceRightsManifestV1:
    """Revalidate the Manifest and every explicitly supplied upstream object/byte anchor."""

    try:
        validated = cast(
            CreativeSampleGeneratedReferenceRightsManifestV1,
            _exact_model(
                manifest, CreativeSampleGeneratedReferenceRightsManifestV1, field="manifest"
            ),
        )
        if artifact is not None:
            if type(artifact) is not CreativeSampleReferenceVisualPromptArtifactV1:
                _invalid("artifact must have its exact public Contract type")
            artifact_sha = creative_sample_reference_visual_prompt_artifact_sha256(artifact)
            if artifact_sha != validated.reference_prompt_artifact_sha256:
                _invalid("Manifest Artifact anchor mismatch")
        if outcome is not None:
            if type(outcome) is not CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1:
                _invalid("outcome must have its exact public Contract type")
            if (
                outcome.outcome_id,
                creative_sample_generated_reference_provider_attempt_outcome_sha256(outcome),
            ) != (validated.provider_attempt_outcome_id, validated.provider_attempt_outcome_sha256):
                _invalid("Manifest Outcome anchor mismatch")
        if candidate is not None:
            if type(candidate) is not CreativeSampleGeneratedReferenceCandidateV1:
                _invalid("candidate must have its exact public Contract type")
            if (
                candidate.candidate_id,
                creative_sample_generated_reference_candidate_sha256(candidate),
            ) != (validated.candidate_id, validated.candidate_sha256):
                _invalid("Manifest Candidate anchor mismatch")
        if qualification_request is not None:
            if (
                type(qualification_request)
                is not CreativeSampleGeneratedReferenceCandidateQualificationRequestV1
            ):
                _invalid("qualification_request must have its exact public Contract type")
            request_projection = (
                creative_sample_generated_reference_candidate_qualification_request_projection(
                    qualification_request
                )
            )
            request_sha = hashlib.sha256(
                b"sdc:generated-reference-candidate-qualification-request:v1\0"
                + _compact_json(request_projection)
            ).hexdigest()
            if (qualification_request.request_id, request_sha) != (
                validated.qualification_request_id,
                validated.qualification_request_sha256,
            ):
                _invalid("Manifest Qualification Request anchor mismatch")
        if qualification_decision is not None:
            if (
                type(qualification_decision)
                is not CreativeSampleGeneratedReferenceCandidateQualificationDecisionV1
            ):
                _invalid("qualification_decision must have its exact public Contract type")
            decision_projection = (
                creative_sample_generated_reference_candidate_qualification_decision_projection(
                    qualification_decision
                )
            )
            decision_sha = hashlib.sha256(
                b"sdc:generated-reference-candidate-qualification-decision:v1\0"
                + _compact_json(decision_projection)
            ).hexdigest()
            if (qualification_decision.decision_id, decision_sha) != (
                validated.qualification_decision_id,
                validated.qualification_decision_sha256,
            ):
                _invalid("Manifest Qualification Decision anchor mismatch")
            if (
                qualification_decision.decision
                != "PASS_FOR_SEPARATE_GENERATED_RIGHTS_MANIFEST_REVIEW"
            ):
                _invalid("Qualification Decision does not permit separate Manifest review")
        if media_bytes is not None:
            if (
                type(media_bytes) is not bytes
                or len(media_bytes) != validated.media_size_bytes
                or _raw_sha256(media_bytes) != validated.media_content_sha256
            ):
                _invalid("Manifest media bytes do not match raw anchors")
        return validated
    except (TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceRightsCurrentStatusError(
            "MANIFEST_CLOSURE_REVALIDATION_FAILED", "Manifest verification failed closed"
        ) from exc


def _admit_retained_json(raw: bytes, *, maximum: int, field: str) -> dict[str, object]:
    if type(raw) is not bytes or not 1 <= len(raw) <= maximum:
        _invalid(f"{field} must contain 1..{maximum} exact bytes")
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw or not raw.endswith(b"\n"):
        _invalid(f"{field} is not canonical UTF-8 document bytes")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_json_no_duplicates,
            parse_constant=lambda item: _invalid(f"non-finite number: {item}"),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{field} is not valid JSON") from exc
    if type(value) is not dict:
        _invalid(f"{field} must contain one JSON object")
    result = cast(dict[str, object], value)
    if _formal_json(result) != raw:
        _invalid(f"{field} is not in exact canonical-document form")
    return result


def _strict_model_from_json_value(
    value: object, expected: type[BaseModel], *, field: str
) -> BaseModel:
    """Normalize only frozen JSON-array fields before strict inline-model validation."""

    if type(value) is not dict:
        _invalid(f"{field} must be one JSON object")
    normalized = dict(cast(dict[str, object], value))
    try:
        if expected is GeneratedReferenceRightsManifestGateResultV1:
            evidence_ids = normalized.get("evidence_record_ids")
            if type(evidence_ids) is not list:
                _invalid(f"{field}.evidence_record_ids must be a JSON array")
            normalized["evidence_record_ids"] = tuple(evidence_ids)
        elif expected is GeneratedReferenceReviewedRightsScopeV1:
            for name in ("territory_scope", "allowed_use_scope"):
                items = normalized.get(name)
                if type(items) is not list:
                    _invalid(f"{field}.{name} must be a JSON array")
                normalized[name] = tuple(items)
        elif expected is GeneratedReferenceCurrentStatusCategoryResultV1:
            for name in ("category_observation_refs", "relied_on_observation_refs"):
                items = normalized.get(name)
                if type(items) is not list:
                    _invalid(f"{field}.{name} must be a JSON array")
                normalized[name] = tuple(
                    GeneratedReferenceCurrentStatusObservationRefV1.model_validate(item)
                    for item in items
                )
        else:
            _invalid(f"{field} has no frozen retained-JSON adapter")
        return expected.model_validate(normalized)
    except ValidationError as exc:
        raise ValueError(f"{field} does not match {expected.__name__}") from exc


def _human_reference(raw: bytes, *, field: str) -> tuple[dict[str, object], str]:
    value = _admit_retained_json(raw, maximum=16_384, field=field)
    if (
        set(value) != {"document_profile", "identity_namespace", "identity_ref"}
        or value.get("document_profile") != "sdc.privacy-minimized-human-reference.v1"
    ):
        _invalid(f"{field} does not use the frozen human-reference profile")
    for key in ("identity_namespace", "identity_ref"):
        item = value.get(key)
        if type(item) is not str or re.fullmatch(_PORTABLE_ID_PATTERN, item) is None:
            _invalid(f"{field}.{key} is not a PortableId")
    return value, _raw_sha256(raw)


def _source_reference(raw: bytes, *, field: str) -> tuple[dict[str, object], str]:
    value = _admit_retained_json(raw, maximum=16_384, field=field)
    if (
        set(value)
        != {
            "document_profile",
            "source_identity_namespace",
            "source_identity_ref",
        }
        or value.get("document_profile") != "sdc.privacy-minimized-source-reference.v1"
    ):
        _invalid(f"{field} does not use the frozen source-reference profile")
    for key in ("source_identity_namespace", "source_identity_ref"):
        item = value.get(key)
        if type(item) is not str or re.fullmatch(_PORTABLE_ID_PATTERN, item) is None:
            _invalid(f"{field}.{key} is not a PortableId")
    return value, _raw_sha256(raw)


def _admit_qualification_evidence(
    values: tuple[GeneratedReferenceQualificationEvidenceInput, ...],
) -> tuple[tuple[GeneratedReferenceQualificationEvidenceReferenceV1, ...], tuple[str, ...]]:
    if type(values) is not tuple or len(values) != 10:
        _invalid("qualification_evidence_documents must be an exact ten-item tuple")
    refs: list[GeneratedReferenceQualificationEvidenceReferenceV1] = []
    digests: list[str] = []
    metadata = (
        "record_id",
        "document_profile",
        "observed_at",
        "effective_from",
        "effective_until",
        "evidence_valid_until",
    )
    for index, item in enumerate(values):
        if type(item) is not GeneratedReferenceQualificationEvidenceInput:
            _invalid(f"qualification evidence {index} has the wrong exact input type")
        if type(item.reference) is not GeneratedReferenceQualificationEvidenceReferenceV1:
            _invalid(f"qualification evidence reference {index} has the wrong exact type")
        reference = GeneratedReferenceQualificationEvidenceReferenceV1.model_validate(
            item.reference
        )
        document = _admit_retained_json(
            item.document_bytes, maximum=262_144, field=f"qualification evidence {index}"
        )
        digest = _raw_sha256(item.document_bytes)
        if reference.document_sha256 != digest or reference.document_size_bytes != len(
            item.document_bytes
        ):
            _invalid(f"qualification evidence {index} raw anchor mismatch")
        if document.get("category") != reference.category:
            _invalid(f"qualification evidence {index} category mismatch")
        for name in metadata:
            if document.get(name) != getattr(reference, name):
                _invalid(f"qualification evidence {index} {name} mismatch")
        if "media_type" in document and document["media_type"] != reference.media_type:
            _invalid(f"qualification evidence {index} media_type mismatch")
        refs.append(reference)
        digests.append(digest)
    if len(set(digests)) != 10 or len({item.record_id for item in refs}) != 10:
        _invalid("Qualification evidence documents and record IDs must be unique")
    return tuple(refs), tuple(digests)


def _admit_manifest_evidence(
    values: tuple[GeneratedReferenceRightsManifestEvidenceInput, ...],
) -> tuple[tuple[GeneratedReferenceRightsManifestEvidenceReferenceV1, ...], tuple[str, ...]]:
    if type(values) is not tuple or len(values) != 9:
        _invalid("review_evidence_documents must be an exact nine-item tuple")
    refs: list[GeneratedReferenceRightsManifestEvidenceReferenceV1] = []
    digests: list[str] = []
    metadata = (
        "record_id",
        "document_profile",
        "observed_at",
        "effective_from",
        "effective_until",
        "evidence_valid_until",
    )
    for index, item in enumerate(values):
        if type(item) is not GeneratedReferenceRightsManifestEvidenceInput:
            _invalid(f"Manifest evidence {index} has the wrong exact input type")
        if type(item.reference) is not GeneratedReferenceRightsManifestEvidenceReferenceV1:
            _invalid(f"Manifest evidence reference {index} has the wrong exact type")
        reference = GeneratedReferenceRightsManifestEvidenceReferenceV1.model_validate(
            _explicit_value(item.reference)
        )
        document = _admit_retained_json(
            item.document_bytes, maximum=262_144, field=f"Manifest evidence {index}"
        )
        digest = _raw_sha256(item.document_bytes)
        if reference.document_sha256 != digest or reference.document_size_bytes != len(
            item.document_bytes
        ):
            _invalid(f"Manifest evidence {index} raw anchor mismatch")
        if document.get("category") != reference.category:
            _invalid(f"Manifest evidence {index} category mismatch")
        for name in metadata:
            if document.get(name) != getattr(reference, name):
                _invalid(f"Manifest evidence {index} {name} mismatch")
        if "media_type" in document and document["media_type"] != reference.media_type:
            _invalid(f"Manifest evidence {index} media_type mismatch")
        refs.append(reference)
        digests.append(digest)
    result = tuple(refs)
    if tuple(item.category for item in result) != MANIFEST_REVIEW_EVIDENCE_CATEGORY_ORDER:
        _invalid("Manifest evidence is not in frozen category order")
    if tuple(item.ordinal for item in result) != tuple(range(9)):
        _invalid("Manifest evidence ordinals are not exact")
    if len(set(digests)) != 9 or len({item.record_id for item in result}) != 9:
        _invalid("Manifest evidence documents and record IDs must be unique")
    return result, tuple(digests)


def _exact_retained_action(raw: bytes, *, expected: Mapping[str, object], field: str) -> str:
    actual = _admit_retained_json(raw, maximum=262_144, field=field)
    if not _exact_json_equal(actual, dict(expected)):
        _invalid(f"{field} differs from its exact closed projection")
    return _raw_sha256(raw)


def _external_revalidate(value: BaseModel, expected: type[BaseModel], *, field: str) -> BaseModel:
    if type(value) is not expected:
        _invalid(f"{field} must have exact type {expected.__name__}")
    canonical = _formal_json(value.model_dump(mode="json"))
    return expected.model_validate_json(canonical)


def _manifest_payload_projection_from_values(values: Mapping[str, object]) -> dict[str, object]:
    return {
        "manifest_review_payload_profile": (
            "sdc.generated-reference-rights-manifest-review-payload.v1"
        ),
        "manifest_policy_id": GENERATED_REFERENCE_RIGHTS_MANIFEST_POLICY_ID,
        "manifest_policy_version": GENERATED_REFERENCE_RIGHTS_MANIFEST_POLICY_VERSION,
        "manifest_policy_document_sha256": (
            GENERATED_REFERENCE_RIGHTS_MANIFEST_POLICY_DOCUMENT_SHA256
        ),
        "reference_prompt_artifact_sha256": values["reference_prompt_artifact_sha256"],
        "provider_attempt_outcome_id": values["provider_attempt_outcome_id"],
        "provider_attempt_outcome_sha256": values["provider_attempt_outcome_sha256"],
        "candidate_id": values["candidate_id"],
        "candidate_sha256": values["candidate_sha256"],
        "qualification_request_id": values["qualification_request_id"],
        "qualification_request_sha256": values["qualification_request_sha256"],
        "qualification_decision_id": values["qualification_decision_id"],
        "qualification_decision_sha256": values["qualification_decision_sha256"],
        "subject_id": values["subject_id"],
        "asset_purpose": values["asset_purpose"],
        "profile_id": values["profile_id"],
        "profile_version": values["profile_version"],
        "profile_sha256": values["profile_sha256"],
        "catalog_version": values["catalog_version"],
        "catalog_sha256": values["catalog_sha256"],
        "render_input_sha256": values["render_input_sha256"],
        "prompt_sha256": values["prompt_sha256"],
        "prompt_size_bytes": values["prompt_size_bytes"],
        "prompt_render_receipt_sha256": values["prompt_render_receipt_sha256"],
        "media_content_sha256": values["media_content_sha256"],
        "media_size_bytes": values["media_size_bytes"],
        "media_technical_record_sha256": values["media_technical_record_sha256"],
        "provider": values["provider"],
        "model": values["model"],
        "provider_region": values["provider_region"],
        "provider_terms_snapshot_id": values["provider_terms_snapshot_id"],
        "provider_terms_snapshot_sha256": values["provider_terms_snapshot_sha256"],
        "submitted_at": values["submitted_at"],
        "qualification_decision_at": values["qualification_decision_at"],
        "qualification_valid_until": values["qualification_valid_until"],
        "manifest_at": values["manifest_at"],
        "review_evidence_refs": _explicit_value(values["review_evidence_refs"]),
        "proposed_rights_scope": _explicit_value(values["proposed_rights_scope"]),
        "evidence_scope": "EXPLICIT_FINITE_BOUND_SET_ONLY",
    }


def build_generated_reference_rights_manifest(
    artifact: CreativeSampleReferenceVisualPromptArtifactV1,
    outcome: CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1,
    candidate: CreativeSampleGeneratedReferenceCandidateV1,
    qualification_request: CreativeSampleGeneratedReferenceCandidateQualificationRequestV1,
    qualification_decision: CreativeSampleGeneratedReferenceCandidateQualificationDecisionV1,
    *,
    png_bytes: bytes,
    qualification_evidence_documents: tuple[GeneratedReferenceQualificationEvidenceInput, ...],
    qualification_preparer_identity_bytes: bytes,
    qualification_preparer_action_bytes: bytes,
    qualifier_identity_bytes: bytes,
    qualifier_action_bytes: bytes,
    review_evidence_documents: tuple[GeneratedReferenceRightsManifestEvidenceInput, ...],
    proposed_rights_scope: GeneratedReferenceRightsScopeProposalV1,
    maker_identity_bytes: bytes,
    maker_action_bytes: bytes,
    checker_identity_bytes: bytes,
    checker_action_bytes: bytes,
    manifest_at: str,
) -> CreativeSampleGeneratedReferenceRightsManifestV1:
    """Rebuild the exact ADR-042/043 closure and record one positive scoped Manifest."""

    try:
        art = cast(
            CreativeSampleReferenceVisualPromptArtifactV1,
            _external_revalidate(
                artifact, CreativeSampleReferenceVisualPromptArtifactV1, field="Artifact"
            ),
        )
        out = cast(
            CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1,
            _external_revalidate(
                outcome,
                CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1,
                field="Outcome",
            ),
        )
        cand = cast(
            CreativeSampleGeneratedReferenceCandidateV1,
            _external_revalidate(
                candidate, CreativeSampleGeneratedReferenceCandidateV1, field="Candidate"
            ),
        )
        request = cast(
            CreativeSampleGeneratedReferenceCandidateQualificationRequestV1,
            _external_revalidate(
                qualification_request,
                CreativeSampleGeneratedReferenceCandidateQualificationRequestV1,
                field="Qualification Request",
            ),
        )
        decision = cast(
            CreativeSampleGeneratedReferenceCandidateQualificationDecisionV1,
            _external_revalidate(
                qualification_decision,
                CreativeSampleGeneratedReferenceCandidateQualificationDecisionV1,
                field="Qualification Decision",
            ),
        )
        if type(png_bytes) is not bytes or not 1 <= len(png_bytes) <= 67_108_864:
            _invalid("png_bytes must contain 1..67108864 exact bytes")
        png_sha = _raw_sha256(png_bytes)
        artifact_sha = creative_sample_reference_visual_prompt_artifact_sha256(art)
        outcome_sha = creative_sample_generated_reference_provider_attempt_outcome_sha256(out)
        candidate_sha = creative_sample_generated_reference_candidate_sha256(cand)
        request_sha = creative_sample_generated_reference_candidate_qualification_request_sha256(
            request
        )
        decision_sha = creative_sample_generated_reference_candidate_qualification_decision_sha256(
            decision
        )
        if art.artifact_sha256 != artifact_sha:
            _invalid("Artifact semantic digest drift")
        if out.outcome_sha256 != outcome_sha or out.outcome_id != (
            f"generated_reference_attempt_outcome_v1_{outcome_sha[:20]}"
        ):
            _invalid("Outcome self identity differs from its explicit semantic digest")
        if cand.candidate_sha256 != candidate_sha or cand.candidate_id != (
            f"generated_reference_candidate_v1_{candidate_sha[:20]}"
        ):
            _invalid("Candidate self identity differs from its explicit semantic digest")
        if request.request_sha256 != request_sha or request.request_id != (
            f"generated_reference_candidate_qualification_request_v1_{request_sha[:20]}"
        ):
            _invalid("Qualification Request self identity drift")
        if decision.decision_sha256 != decision_sha or decision.decision_id != (
            f"generated_reference_candidate_qualification_decision_v1_{decision_sha[:20]}"
        ):
            _invalid("Qualification Decision self identity drift")
        if (out.reference_prompt_artifact_sha256, cand.reference_prompt_artifact_sha256) != (
            artifact_sha,
            artifact_sha,
        ):
            _invalid("Outcome/Candidate Artifact closure mismatch")
        if (cand.provider_attempt_outcome_id, cand.provider_attempt_outcome_sha256) != (
            out.outcome_id,
            outcome_sha,
        ):
            _invalid("Candidate Outcome closure mismatch")
        if (cand.media_content_sha256, cand.media_size_bytes) != (png_sha, len(png_bytes)):
            _invalid("Candidate does not bind the exact supplied PNG bytes")
        if len(out.output_descriptors) != 1 or (
            out.output_descriptors[0].content_sha256,
            out.output_descriptors[0].size_bytes,
            out.output_descriptors[0].technical_record_sha256,
        ) != (png_sha, len(png_bytes), cand.media_technical_record_sha256):
            _invalid("Outcome output descriptor does not close the exact PNG")
        if (request.candidate_id, request.candidate_sha256) != (
            cand.candidate_id,
            candidate_sha,
        ) or (request.provider_attempt_outcome_id, request.provider_attempt_outcome_sha256) != (
            out.outcome_id,
            outcome_sha,
        ):
            _invalid("Qualification Request does not bind Candidate/Outcome")
        if (decision.request_id, decision.request_sha256) != (
            request.request_id,
            request.request_sha256,
        ) or (decision.candidate_id, decision.candidate_sha256) != (
            cand.candidate_id,
            candidate_sha,
        ):
            _invalid("Qualification Decision does not bind Request/Candidate")
        if (
            decision.decision != "PASS_FOR_SEPARATE_GENERATED_RIGHTS_MANIFEST_REVIEW"
            or decision.eligible_for_separate_generated_rights_manifest_review is not True
            or decision.qualification_performed is not True
            or decision.rights_manifest_embedded is not False
            or decision.current_status_assessment_embedded is not False
            or decision.eligible_for_asset_promotion is not False
        ):
            _invalid("Qualification Decision is not the exact positive zero-authority outcome")
        manifest_at = _utc_seconds(manifest_at, field="manifest_at")
        if (
            not _parse_utc(decision.decision_at, field="decision_at")
            <= _parse_utc(manifest_at, field="manifest_at")
            < _parse_utc(decision.qualification_valid_until, field="qualification_valid_until")
        ):
            _invalid("Qualification Decision is expired or later than manifest_at")
        qualification_refs, qualification_digests = _admit_qualification_evidence(
            qualification_evidence_documents
        )
        if qualification_refs != request.evidence_refs:
            _invalid("Qualification evidence does not exactly rebuild the Request")
        record_by_category: dict[str, str] = {
            item.category: item.record_id for item in qualification_refs
        }
        for ordinal, gate_result in enumerate(decision.gate_results):
            expected_evidence_ids = tuple(
                record_by_category[category]
                for category in _QUALIFICATION_GATE_EVIDENCE_CATEGORIES[ordinal]
            )
            if gate_result.evidence_record_ids != expected_evidence_ids:
                _invalid("Qualification Decision gate evidence mapping drift")
        preparer_identity, preparer_identity_sha = _human_reference(
            qualification_preparer_identity_bytes, field="Qualification Preparer identity"
        )
        qualifier_identity, qualifier_identity_sha = _human_reference(
            qualifier_identity_bytes, field="Qualification qualifier identity"
        )
        if preparer_identity_sha != request.evidence_preparer_ref_sha256:
            _invalid("Qualification Preparer identity anchor mismatch")
        preparer_expected = {
            "document_profile": (
                "sdc.generated-reference-qualification-request-preparation-action.v1"
            ),
            "action": "PREPARED_GENERATED_REFERENCE_QUALIFICATION_EVIDENCE",
            "actor_ref_sha256": preparer_identity_sha,
            "candidate_sha256": cand.candidate_sha256,
            "provider_attempt_outcome_sha256": out.outcome_sha256,
            "policy_document_sha256": request.policy_document_sha256,
            "requested_at": request.requested_at,
            "evidence_document_sha256s": list(qualification_digests),
        }
        preparer_action_sha = _exact_retained_action(
            qualification_preparer_action_bytes,
            expected=preparer_expected,
            field="Qualification Preparer action",
        )
        if preparer_action_sha != request.evidence_preparer_record_sha256:
            _invalid("Qualification Preparer action anchor mismatch")
        qualifier_expected = {
            "document_profile": "sdc.generated-reference-qualification-decision-action.v1",
            "action": "RECORDED_GENERATED_REFERENCE_QUALIFICATION_DECISION",
            "actor_ref_sha256": qualifier_identity_sha,
            "request_sha256": request.request_sha256,
            "decision_at": decision.decision_at,
            "gate_results": [item.model_dump(mode="json") for item in decision.gate_results],
            "qualification_issue_codes": list(decision.qualification_issue_codes),
            "qualification_basis": decision.qualification_basis,
            "decision": decision.decision,
            "eligible_for_separate_generated_rights_manifest_review": True,
        }
        qualifier_action_sha = _exact_retained_action(
            qualifier_action_bytes,
            expected=qualifier_expected,
            field="Qualification qualifier action",
        )
        if (
            qualifier_identity_sha != decision.qualifier_ref_sha256
            or qualifier_action_sha != decision.qualifier_record_sha256
        ):
            _invalid("Qualification qualifier retained anchors mismatch")
        review_refs, review_digests = _admit_manifest_evidence(review_evidence_documents)
        proposal = cast(
            GeneratedReferenceRightsScopeProposalV1,
            _exact_model(
                proposed_rights_scope,
                GeneratedReferenceRightsScopeProposalV1,
                field="proposed_rights_scope",
            ),
        )
        maker_identity, maker_identity_sha = _human_reference(
            maker_identity_bytes, field="Manifest Maker identity"
        )
        checker_identity, checker_identity_sha = _human_reference(
            checker_identity_bytes, field="Manifest Checker identity"
        )
        identity_tuples = (
            (maker_identity["identity_namespace"], maker_identity["identity_ref"]),
            (checker_identity["identity_namespace"], checker_identity["identity_ref"]),
            (qualifier_identity["identity_namespace"], qualifier_identity["identity_ref"]),
        )
        if identity_tuples[0] == identity_tuples[1] or identity_tuples[1] == identity_tuples[2]:
            _invalid("Manifest Maker/Checker/Qualifier role separation failed")
        snapshot = art.profile_snapshot
        values: dict[str, object] = {
            "reference_prompt_artifact_sha256": artifact_sha,
            "provider_attempt_outcome_id": out.outcome_id,
            "provider_attempt_outcome_sha256": outcome_sha,
            "candidate_id": cand.candidate_id,
            "candidate_sha256": candidate_sha,
            "qualification_request_id": request.request_id,
            "qualification_request_sha256": request.request_sha256,
            "qualification_decision_id": decision.decision_id,
            "qualification_decision_sha256": decision.decision_sha256,
            "subject_id": cand.subject_id,
            "asset_purpose": cand.asset_purpose,
            "profile_id": snapshot.profile_id,
            "profile_version": snapshot.profile_version,
            "profile_sha256": snapshot.profile_sha256,
            "catalog_version": snapshot.catalog_version,
            "catalog_sha256": snapshot.catalog_sha256,
            "render_input_sha256": art.render_input_sha256,
            "prompt_sha256": art.prompt_sha256,
            "prompt_size_bytes": len(art.prompt.encode("utf-8")),
            "prompt_render_receipt_sha256": art.prompt_render_receipt.prompt_render_receipt_sha256,
            "media_content_sha256": png_sha,
            "media_size_bytes": len(png_bytes),
            "media_technical_record_sha256": cand.media_technical_record_sha256,
            "provider": out.provider,
            "model": out.model,
            "provider_region": out.provider_region,
            "provider_terms_snapshot_id": out.provider_terms_snapshot_id,
            "provider_terms_snapshot_sha256": out.provider_terms_snapshot_sha256,
            "submitted_at": out.submitted_at,
            "qualification_decision_at": decision.decision_at,
            "qualification_valid_until": decision.qualification_valid_until,
            "manifest_at": manifest_at,
            "review_evidence_refs": review_refs,
            "proposed_rights_scope": proposal,
        }
        payload_sha = _semantic_sha256(
            GENERATED_REFERENCE_RIGHTS_MANIFEST_REVIEW_PAYLOAD_SHA256_DOMAIN,
            _manifest_payload_projection_from_values(values),
        )
        maker_action = _admit_retained_json(
            maker_action_bytes, maximum=262_144, field="Manifest Maker action"
        )
        maker_prepared_at = maker_action.get("prepared_at")
        if type(maker_prepared_at) is not str:
            _invalid("Manifest Maker action lacks prepared_at")
        maker_expected = {
            "document_profile": (
                "sdc.generated-reference-rights-manifest-review-preparation-action.v1"
            ),
            "action": "PREPARED_GENERATED_REFERENCE_RIGHTS_MANIFEST_REVIEW",
            "actor_identity_ref_sha256": maker_identity_sha,
            "manifest_review_payload_sha256": payload_sha,
            "prepared_at": maker_prepared_at,
        }
        maker_action_sha = _exact_retained_action(
            maker_action_bytes, expected=maker_expected, field="Manifest Maker action"
        )
        checker_action = _admit_retained_json(
            checker_action_bytes, maximum=262_144, field="Manifest Checker action"
        )
        if set(checker_action) != {
            "document_profile",
            "action",
            "actor_identity_ref_sha256",
            "manifest_review_payload_sha256",
            "maker_action_sha256",
            "reviewed_at",
            "gate_results",
            "reviewed_rights_scope",
            "disposition",
        }:
            _invalid("Manifest Checker action fields differ from frozen projection")
        raw_gate_results = checker_action["gate_results"]
        if type(raw_gate_results) is not list:
            _invalid("Manifest Checker action gate_results must be a JSON array")
        gate_results = tuple(
            cast(
                GeneratedReferenceRightsManifestGateResultV1,
                _strict_model_from_json_value(
                    item,
                    GeneratedReferenceRightsManifestGateResultV1,
                    field=f"Manifest Checker action gate_results[{index}]",
                ),
            )
            for index, item in enumerate(raw_gate_results)
        )
        reviewed_scope = cast(
            GeneratedReferenceReviewedRightsScopeV1,
            _strict_model_from_json_value(
                checker_action["reviewed_rights_scope"],
                GeneratedReferenceReviewedRightsScopeV1,
                field="Manifest Checker action reviewed_rights_scope",
            ),
        )
        checker_expected = {
            "document_profile": "sdc.generated-reference-rights-manifest-review-checker-action.v1",
            "action": "RECORDED_GENERATED_REFERENCE_RIGHTS_MANIFEST_REVIEW",
            "actor_identity_ref_sha256": checker_identity_sha,
            "manifest_review_payload_sha256": payload_sha,
            "maker_action_sha256": maker_action_sha,
            "reviewed_at": manifest_at,
            "gate_results": _explicit_value(gate_results),
            "reviewed_rights_scope": _explicit_value(reviewed_scope),
            "disposition": "PASS_FOR_SEPARATE_GENERATED_CURRENT_STATUS_ASSESSMENT",
        }
        checker_action_sha = _exact_retained_action(
            checker_action_bytes, expected=checker_expected, field="Manifest Checker action"
        )
        retained_digests = (
            preparer_identity_sha,
            preparer_action_sha,
            qualifier_identity_sha,
            qualifier_action_sha,
            maker_identity_sha,
            maker_action_sha,
            checker_identity_sha,
            checker_action_sha,
            *qualification_digests,
            *review_digests,
        )
        formal_forbidden = {
            GENERATED_REFERENCE_RIGHTS_MANIFEST_POLICY_DOCUMENT_SHA256,
            GENERATED_REFERENCE_CURRENT_STATUS_POLICY_DOCUMENT_SHA256,
            *_collect_sha256_strings(art.model_dump(mode="json")),
            *_collect_sha256_strings(out.model_dump(mode="json")),
            *_collect_sha256_strings(cand.model_dump(mode="json")),
            *_collect_sha256_strings(request.model_dump(mode="json")),
            *_collect_sha256_strings(decision.model_dump(mode="json")),
        }
        _reject_retained_digest_aliases(
            retained_digests,
            forbidden=formal_forbidden,
            field="Manifest closure",
        )
        values.update(
            {
                "manifest_review_payload_sha256": payload_sha,
                "gate_results": gate_results,
                "reviewed_rights_scope": reviewed_scope,
                "maker_identity_ref_sha256": maker_identity_sha,
                "maker_action_sha256": maker_action_sha,
                "maker_prepared_at": maker_prepared_at,
                "checker_identity_ref_sha256": checker_identity_sha,
                "checker_action_sha256": checker_action_sha,
                "checker_reviewed_at": manifest_at,
            }
        )
        return _build_generated_reference_rights_manifest_from_values(values)
    except (TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceRightsCurrentStatusError(
            "MANIFEST_CLOSURE_REVALIDATION_FAILED",
            "typed upstream and retained-byte Manifest construction failed closed",
        ) from exc


def verify_generated_reference_rights_manifest(
    manifest: CreativeSampleGeneratedReferenceRightsManifestV1,
    artifact: CreativeSampleReferenceVisualPromptArtifactV1,
    outcome: CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1,
    candidate: CreativeSampleGeneratedReferenceCandidateV1,
    qualification_request: CreativeSampleGeneratedReferenceCandidateQualificationRequestV1,
    qualification_decision: CreativeSampleGeneratedReferenceCandidateQualificationDecisionV1,
    *,
    png_bytes: bytes,
    qualification_evidence_documents: tuple[GeneratedReferenceQualificationEvidenceInput, ...],
    qualification_preparer_identity_bytes: bytes,
    qualification_preparer_action_bytes: bytes,
    qualifier_identity_bytes: bytes,
    qualifier_action_bytes: bytes,
    review_evidence_documents: tuple[GeneratedReferenceRightsManifestEvidenceInput, ...],
    proposed_rights_scope: GeneratedReferenceRightsScopeProposalV1,
    maker_identity_bytes: bytes,
    maker_action_bytes: bytes,
    checker_identity_bytes: bytes,
    checker_action_bytes: bytes,
    manifest_at: str,
) -> CreativeSampleGeneratedReferenceRightsManifestV1:
    """Rebuild a Manifest from the complete typed/raw closure and require exact equality."""

    try:
        validated = cast(
            CreativeSampleGeneratedReferenceRightsManifestV1,
            _exact_model(
                manifest,
                CreativeSampleGeneratedReferenceRightsManifestV1,
                field="manifest",
            ),
        )
        rebuilt = build_generated_reference_rights_manifest(
            artifact,
            outcome,
            candidate,
            qualification_request,
            qualification_decision,
            png_bytes=png_bytes,
            qualification_evidence_documents=qualification_evidence_documents,
            qualification_preparer_identity_bytes=qualification_preparer_identity_bytes,
            qualification_preparer_action_bytes=qualification_preparer_action_bytes,
            qualifier_identity_bytes=qualifier_identity_bytes,
            qualifier_action_bytes=qualifier_action_bytes,
            review_evidence_documents=review_evidence_documents,
            proposed_rights_scope=proposed_rights_scope,
            maker_identity_bytes=maker_identity_bytes,
            maker_action_bytes=maker_action_bytes,
            checker_identity_bytes=checker_identity_bytes,
            checker_action_bytes=checker_action_bytes,
            manifest_at=manifest_at,
        )
        if rebuilt != validated:
            _invalid("Manifest differs from the complete freshly rebuilt closure")
        return validated
    except (TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceRightsCurrentStatusError(
            "MANIFEST_CLOSURE_REVALIDATION_FAILED", "Manifest verification failed closed"
        ) from exc


def _build_generated_reference_current_status_request_contract(
    *,
    subject_closure: GeneratedReferenceCurrentStatusSubjectClosureV1,
    status_preparer_identity_bytes: bytes,
    status_preparer_action_bytes: bytes,
    requested_at: str,
    observation_refs: Sequence[GeneratedReferenceCurrentStatusObservationRefV1],
    request_basis: str,
) -> CreativeSampleGeneratedReferenceCurrentStatusRequestV1:
    try:
        closure = cast(
            GeneratedReferenceCurrentStatusSubjectClosureV1,
            _exact_model(
                subject_closure,
                GeneratedReferenceCurrentStatusSubjectClosureV1,
                field="subject_closure",
            ),
        )
        if (
            type(status_preparer_identity_bytes) is not bytes
            or not 1 <= len(status_preparer_identity_bytes) <= 16_384
        ):
            _invalid("status_preparer_identity_bytes must contain 1..16384 exact bytes")
        if (
            type(status_preparer_action_bytes) is not bytes
            or not 1 <= len(status_preparer_action_bytes) <= 262_144
        ):
            _invalid("status_preparer_action_bytes must contain 1..262144 exact bytes")
        requested = _parse_utc(requested_at, field="requested_at")
        valid_until = min(
            requested + timedelta(seconds=86_400),
            _parse_utc(closure.manifest_valid_until, field="manifest_valid_until"),
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        category_index = {
            category: index for index, category in enumerate(CURRENT_STATUS_CATEGORY_ORDER)
        }
        refs = tuple(
            sorted(
                (
                    cast(
                        GeneratedReferenceCurrentStatusObservationRefV1,
                        _exact_model(
                            ref,
                            GeneratedReferenceCurrentStatusObservationRefV1,
                            field="observation_ref",
                        ),
                    )
                    for ref in observation_refs
                ),
                key=lambda item: (
                    category_index[item.category],
                    item.valid_from,
                    item.observation_id,
                ),
            )
        )
        canonical_refs = tuple(
            GeneratedReferenceCurrentStatusObservationRefV1.model_validate(
                {**cast(dict[str, object], _explicit_value(ref)), "ordinal": index}
            )
            for index, ref in enumerate(refs)
        )
        values = {
            **_base_current_values(),
            "document_type": "sdc.creative-sample-generated-reference-current-status-request-v1",
            "request_scope": "GENERATED_REFERENCE_CURRENT_STATUS_ASSESSMENT_ONLY",
            "subject_closure": closure,
            "status_preparer_identity_ref_sha256": _raw_sha256(status_preparer_identity_bytes),
            "status_preparer_action_sha256": _raw_sha256(status_preparer_action_bytes),
            "requested_at": requested_at,
            "request_valid_until": valid_until,
            "observation_refs": canonical_refs,
            "request_basis": request_basis,
            "status": "GENERATED_CURRENT_STATUS_REQUESTED",
        }
        return cast(
            CreativeSampleGeneratedReferenceCurrentStatusRequestV1,
            _build_identity_contract(
                CreativeSampleGeneratedReferenceCurrentStatusRequestV1,
                values=values,
                id_field="request_id",
                sha_field="request_sha256",
                stem="generated_reference_current_status_request_v1_",
                domain=GENERATED_REFERENCE_CURRENT_STATUS_REQUEST_SHA256_DOMAIN,
            ),
        )
    except (TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceRightsCurrentStatusError(
            "REQUEST_CONTRACT_INVALID", "Request construction failed"
        ) from exc


def _build_generated_reference_current_status_instruction_contract(
    *,
    request: CreativeSampleGeneratedReferenceCurrentStatusRequestV1,
    status_checker_identity_bytes: bytes,
    status_checker_action_bytes: bytes,
    evaluated_at: str,
    category_results: tuple[GeneratedReferenceCurrentStatusCategoryResultV1, ...],
    checker_basis: str,
) -> CreativeSampleGeneratedReferenceCurrentStatusInstructionV1:
    try:
        validated = cast(
            CreativeSampleGeneratedReferenceCurrentStatusRequestV1,
            _exact_model(
                request, CreativeSampleGeneratedReferenceCurrentStatusRequestV1, field="request"
            ),
        )
        if (
            type(status_checker_identity_bytes) is not bytes
            or not 1 <= len(status_checker_identity_bytes) <= 16_384
        ):
            _invalid("status_checker_identity_bytes must contain 1..16384 exact bytes")
        if (
            type(status_checker_action_bytes) is not bytes
            or not 1 <= len(status_checker_action_bytes) <= 262_144
        ):
            _invalid("status_checker_action_bytes must contain 1..262144 exact bytes")
        checker_identity_sha = _raw_sha256(status_checker_identity_bytes)
        checker_action_sha = _raw_sha256(status_checker_action_bytes)
        if (
            checker_identity_sha == validated.status_preparer_identity_ref_sha256
            or checker_action_sha == validated.status_preparer_action_sha256
        ):
            _invalid("status Preparer and Checker identities/actions must be distinct")
        evaluated = _parse_utc(evaluated_at, field="evaluated_at")
        if (
            not _parse_utc(validated.requested_at, field="requested_at")
            <= evaluated
            < _parse_utc(validated.request_valid_until, field="request_valid_until")
        ):
            _invalid("evaluated_at lies outside Request window")
        _validate_category_results(category_results)
        values = {
            **_base_current_values(),
            "document_type": (
                "sdc.creative-sample-generated-reference-current-status-instruction-v1"
            ),
            "instruction_scope": "GENERATED_REFERENCE_CURRENT_STATUS_ASSESSMENT_ONLY",
            "request_id": validated.request_id,
            "request_sha256": validated.request_sha256,
            "subject_closure": validated.subject_closure,
            "status_preparer_identity_ref_sha256": validated.status_preparer_identity_ref_sha256,
            "status_preparer_action_sha256": validated.status_preparer_action_sha256,
            "status_checker_identity_ref_sha256": checker_identity_sha,
            "status_checker_action_sha256": checker_action_sha,
            "requested_at": validated.requested_at,
            "request_valid_until": validated.request_valid_until,
            "evaluated_at": evaluated_at,
            "category_results": category_results,
            "checker_basis": checker_basis,
            "status": "GENERATED_CURRENT_STATUS_INSTRUCTION_RECORDED",
        }
        return cast(
            CreativeSampleGeneratedReferenceCurrentStatusInstructionV1,
            _build_identity_contract(
                CreativeSampleGeneratedReferenceCurrentStatusInstructionV1,
                values=values,
                id_field="instruction_id",
                sha_field="instruction_sha256",
                stem="generated_reference_current_status_instruction_v1_",
                domain=GENERATED_REFERENCE_CURRENT_STATUS_INSTRUCTION_SHA256_DOMAIN,
            ),
        )
    except (TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceRightsCurrentStatusError(
            "INSTRUCTION_CONTRACT_INVALID", "Instruction construction failed"
        ) from exc


def _build_generated_reference_current_status_decision_contract(
    *,
    request: CreativeSampleGeneratedReferenceCurrentStatusRequestV1,
    instruction: CreativeSampleGeneratedReferenceCurrentStatusInstructionV1,
) -> CreativeSampleGeneratedReferenceCurrentStatusDecisionV1:
    try:
        req = cast(
            CreativeSampleGeneratedReferenceCurrentStatusRequestV1,
            _exact_model(
                request, CreativeSampleGeneratedReferenceCurrentStatusRequestV1, field="request"
            ),
        )
        inst = cast(
            CreativeSampleGeneratedReferenceCurrentStatusInstructionV1,
            _exact_model(
                instruction,
                CreativeSampleGeneratedReferenceCurrentStatusInstructionV1,
                field="instruction",
            ),
        )
        if (inst.request_id, inst.request_sha256, inst.subject_closure) != (
            req.request_id,
            req.request_sha256,
            req.subject_closure,
        ):
            _invalid("Instruction does not close the exact Request")
        recorded_status, revoked, held, indeterminate = _derive_status_and_diagnostics(
            inst.category_results
        )
        status_valid_until = min(item.result_valid_until for item in inst.category_results)
        values = {
            **_base_current_values(),
            "document_type": "sdc.creative-sample-generated-reference-current-status-decision-v1",
            "decision_scope": "GENERATED_REFERENCE_CURRENT_STATUS_ASSESSMENT_ONLY",
            "request_id": req.request_id,
            "request_sha256": req.request_sha256,
            "instruction_id": inst.instruction_id,
            "instruction_sha256": inst.instruction_sha256,
            "subject_closure": req.subject_closure,
            "evaluated_at": inst.evaluated_at,
            "decision_at": inst.evaluated_at,
            "status_valid_until": status_valid_until,
            "category_results": inst.category_results,
            "revoked_categories": revoked,
            "held_categories": held,
            "indeterminate_categories": indeterminate,
            "recorded_status": recorded_status,
            "status": "GENERATED_CURRENT_STATUS_DECISION_RECORDED",
        }
        return cast(
            CreativeSampleGeneratedReferenceCurrentStatusDecisionV1,
            _build_identity_contract(
                CreativeSampleGeneratedReferenceCurrentStatusDecisionV1,
                values=values,
                id_field="decision_id",
                sha_field="decision_sha256",
                stem="generated_reference_current_status_decision_v1_",
                domain=GENERATED_REFERENCE_CURRENT_STATUS_DECISION_SHA256_DOMAIN,
            ),
        )
    except (TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceRightsCurrentStatusError(
            "DECISION_CONTRACT_INVALID", "Decision construction failed"
        ) from exc


def _build_generated_reference_current_status_evidence_record_contract(
    *,
    request: CreativeSampleGeneratedReferenceCurrentStatusRequestV1,
    instruction: CreativeSampleGeneratedReferenceCurrentStatusInstructionV1,
    decision: CreativeSampleGeneratedReferenceCurrentStatusDecisionV1,
) -> CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1:
    try:
        req = cast(
            CreativeSampleGeneratedReferenceCurrentStatusRequestV1,
            _exact_model(
                request, CreativeSampleGeneratedReferenceCurrentStatusRequestV1, field="request"
            ),
        )
        inst = cast(
            CreativeSampleGeneratedReferenceCurrentStatusInstructionV1,
            _exact_model(
                instruction,
                CreativeSampleGeneratedReferenceCurrentStatusInstructionV1,
                field="instruction",
            ),
        )
        dec = cast(
            CreativeSampleGeneratedReferenceCurrentStatusDecisionV1,
            _exact_model(
                decision, CreativeSampleGeneratedReferenceCurrentStatusDecisionV1, field="decision"
            ),
        )
        values = {
            **_base_current_values(),
            "document_type": (
                "sdc.creative-sample-generated-reference-current-status-evidence-record-v1"
            ),
            "record_scope": "GENERATED_REFERENCE_CURRENT_STATUS_EVIDENCE_CLOSURE_ONLY",
            "subject_closure": req.subject_closure,
            "request": req,
            "instruction": inst,
            "decision": dec,
            "status": "GENERATED_CURRENT_STATUS_EVIDENCE_RECORDED",
        }
        return cast(
            CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1,
            _build_identity_contract(
                CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1,
                values=values,
                id_field="record_id",
                sha_field="record_sha256",
                stem="generated_reference_current_status_evidence_record_v1_",
                domain=GENERATED_REFERENCE_CURRENT_STATUS_EVIDENCE_RECORD_SHA256_DOMAIN,
            ),
        )
    except (TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceRightsCurrentStatusError(
            "EVIDENCE_RECORD_INVALID", "Evidence Record construction failed"
        ) from exc


@dataclass(frozen=True, slots=True)
class GeneratedReferenceCurrentStatusObservationInput:
    observation: CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1
    document_bytes: bytes


@dataclass(frozen=True, slots=True)
class GeneratedReferenceCurrentStatusExplicitChainInput:
    target_observation_refs: tuple[GeneratedReferenceCurrentStatusObservationRefV1, ...]
    observation_inputs: tuple[GeneratedReferenceCurrentStatusObservationInput, ...]


def _admit_observation_input(
    value: GeneratedReferenceCurrentStatusObservationInput,
) -> CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1:
    if type(value) is not GeneratedReferenceCurrentStatusObservationInput:
        _invalid("Observation input has the wrong exact process type")
    observation = cast(
        CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1,
        _exact_model(
            value.observation,
            CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1,
            field="observation",
        ),
    )
    if type(value.document_bytes) is not bytes or value.document_bytes != (
        generated_reference_contract_document_bytes(observation)
    ):
        _invalid("Observation canonical document bytes do not match the exact typed Contract")
    return observation


@dataclass(frozen=True, slots=True)
class GeneratedReferenceCurrentStatusChainReplayResult:
    chain_scope_sha256: str
    genesis_observation_id: str
    observation_set_sha256: str
    target_observation_refs: tuple[GeneratedReferenceCurrentStatusObservationRefV1, ...]
    observation_occurrences: tuple[dict[str, str], ...]
    observations: tuple[CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1, ...]
    _ancestor_ids_by_observation_id: Mapping[str, frozenset[str]]


@dataclass(frozen=True, slots=True)
class GeneratedReferenceCurrentStatusChainCoverageResult:
    explicit_chain_set_sha256: str
    coverage_set_sha256: str
    chain_results: tuple[GeneratedReferenceCurrentStatusChainReplayResult, ...]
    target_coverage: tuple[dict[str, object], ...]
    category_results: tuple[GeneratedReferenceCurrentStatusCategoryResultV1, ...]


@dataclass(frozen=True, slots=True)
class GeneratedReferenceCurrentStatusJointReplayResult:
    explicit_chain_set_sha256: str
    coverage_set_sha256: str
    joint_replay_sha256: str
    category_results: tuple[GeneratedReferenceCurrentStatusCategoryResultV1, ...]
    recorded_status: CurrentStatusResult
    _coverage: GeneratedReferenceCurrentStatusChainCoverageResult


_ASSESSMENT_GUARD = object()


@dataclass(frozen=True, slots=True)
class GeneratedReferenceCurrentStatusAsOfAssessmentResult:
    record_id: str
    record_sha256: str
    request_id: str
    request_sha256: str
    decision_id: str
    decision_sha256: str
    subject_closure: GeneratedReferenceCurrentStatusSubjectClosureV1
    explicit_chain_set_sha256: str
    coverage_set_sha256: str
    joint_replay_sha256: str
    as_of_assessment_sha256: str
    as_of: str
    evaluated_at: str
    status_valid_until: str
    recorded_status: CurrentStatusResult
    as_of_status: CurrentStatusResult
    recorded_revoked_categories: tuple[CurrentStatusCategory, ...]
    recorded_held_categories: tuple[CurrentStatusCategory, ...]
    recorded_indeterminate_categories: tuple[CurrentStatusCategory, ...]
    limitation_codes: tuple[CurrentStatusLimitationCode, ...]
    _provenance_sha256: str
    _guard: object


def generated_reference_current_status_chain_head(
    observation: CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1,
) -> GeneratedReferenceCurrentStatusChainHeadRefV1:
    validated = cast(
        CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1,
        _exact_model(
            observation,
            CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1,
            field="observation",
        ),
    )
    return GeneratedReferenceCurrentStatusChainHeadRefV1(
        observation_id=validated.observation_id,
        observation_sha256=validated.observation_sha256,
        chain_sha256=generated_reference_current_status_chain_sha256(validated),
    )


def _transition_valid(
    observation: CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1,
    predecessors: tuple[CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1, ...],
) -> bool:
    basis = observation.basis_code
    claim = observation.claim_value
    specific_present = basis in _BASIS_MATRIX[observation.category]["PRESENT"]
    specific_absent = basis in _BASIS_MATRIX[observation.category]["ABSENT_WITH_EVIDENCE"]
    if observation.chain_link.link_kind == "GENESIS":
        return (
            (specific_present and claim == "PRESENT")
            or (specific_absent and claim == "ABSENT_WITH_EVIDENCE")
            or (basis == "INITIAL_STATUS_UNKNOWN" and claim == "UNKNOWN")
            or (basis == "INITIAL_STATUS_NOT_ASSESSED" and claim == "NOT_ASSESSED")
            or (basis == "CONFLICT_IDENTIFIED" and claim == "CONFLICT")
        )
    if observation.chain_link.link_kind == "SUCCESSOR":
        previous = predecessors[0].claim_value
        if previous == "NOT_ASSESSED":
            return (
                (basis == "INITIAL_STATUS_UNKNOWN" and claim == "UNKNOWN")
                or (specific_present and claim == "PRESENT")
                or (specific_absent and claim == "ABSENT_WITH_EVIDENCE")
                or (basis == "CONFLICT_IDENTIFIED" and claim == "CONFLICT")
            )
        if previous == "UNKNOWN":
            return (
                (specific_present and claim == "PRESENT")
                or (specific_absent and claim == "ABSENT_WITH_EVIDENCE")
                or (basis == "CONFLICT_IDENTIFIED" and claim == "CONFLICT")
            )
        if previous == "PRESENT":
            return (
                (basis == "STATUS_RECONFIRMED" and claim == "PRESENT")
                or (specific_absent and claim == "ABSENT_WITH_EVIDENCE")
                or (basis == "STATUS_BECAME_UNKNOWN" and claim == "UNKNOWN")
                or (basis == "CONFLICT_IDENTIFIED" and claim == "CONFLICT")
            )
        if previous == "ABSENT_WITH_EVIDENCE":
            return (
                (basis == "STATUS_RECONFIRMED" and claim == "ABSENT_WITH_EVIDENCE")
                or (specific_present and claim == "PRESENT")
                or (basis == "STATUS_BECAME_UNKNOWN" and claim == "UNKNOWN")
                or (basis == "CONFLICT_IDENTIFIED" and claim == "CONFLICT")
            )
        return False
    if basis == "CONFLICT_RECONCILED":
        return claim in {"PRESENT", "ABSENT_WITH_EVIDENCE", "UNKNOWN"}
    if basis == "CONFLICT_IDENTIFIED":
        return claim == "CONFLICT"
    return False


def replay_generated_reference_current_status_chain(
    chain_input: GeneratedReferenceCurrentStatusExplicitChainInput,
) -> GeneratedReferenceCurrentStatusChainReplayResult:
    try:
        if type(chain_input) is not GeneratedReferenceCurrentStatusExplicitChainInput:
            raise GeneratedReferenceChainReplayError(
                "COUNT_OUT_OF_RANGE", "chain_input must have its exact process type"
            )
        if (
            not 1 <= len(chain_input.observation_inputs) <= 64
            or not 1 <= len(chain_input.target_observation_refs) <= 32
        ):
            raise GeneratedReferenceChainReplayError(
                "COUNT_OUT_OF_RANGE", "chain occurrence or target count is out of range"
            )
        try:
            observations = tuple(
                _admit_observation_input(item) for item in chain_input.observation_inputs
            )
            targets = tuple(
                cast(
                    GeneratedReferenceCurrentStatusObservationRefV1,
                    _exact_model(
                        item,
                        GeneratedReferenceCurrentStatusObservationRefV1,
                        field="target_observation_ref",
                    ),
                )
                for item in chain_input.target_observation_refs
            )
        except (TypeError, ValueError, ValidationError) as exc:
            raise GeneratedReferenceChainReplayError(
                "OBSERVATION_CONTRACT_INVALID", "an Observation or target reference is invalid"
            ) from exc
        ids = tuple(item.observation_id for item in observations)
        document_shas = tuple(item.observation_sha256 for item in observations)
        chain_shas = tuple(
            generated_reference_current_status_chain_sha256(item) for item in observations
        )
        if len(ids) != len(set(ids)):
            raise GeneratedReferenceChainReplayError(
                "DUPLICATE_OBSERVATION_ID", "Observation IDs must be unique"
            )
        if len(document_shas) != len(set(document_shas)):
            raise GeneratedReferenceChainReplayError(
                "DUPLICATE_OBSERVATION_DOCUMENT_SHA256",
                "Observation semantic SHA values must be unique",
            )
        if len(chain_shas) != len(set(chain_shas)):
            raise GeneratedReferenceChainReplayError(
                "DUPLICATE_OBSERVATION_CHAIN_SHA256", "Observation chain SHA values must be unique"
            )
        scopes = {item.chain_link.chain_scope_sha256 for item in observations}
        if len(scopes) != 1 or any(target.chain_scope_sha256 not in scopes for target in targets):
            raise GeneratedReferenceChainReplayError(
                "CHAIN_SCOPE_MISMATCH", "one logical chain must use one chain scope"
            )
        by_id = dict(zip(ids, observations, strict=True))
        chain_by_id = dict(zip(ids, chain_shas, strict=True))
        predecessor_ids: dict[str, tuple[str, ...]] = {}
        for observation in observations:
            resolved: list[CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1] = []
            for head in observation.chain_link.predecessor_heads:
                predecessor = by_id.get(head.observation_id)
                if predecessor is None:
                    raise GeneratedReferenceChainReplayError(
                        "ORPHAN_REFERENCE", "predecessor is absent from explicit chain"
                    )
                if (head.observation_sha256, head.chain_sha256) != (
                    predecessor.observation_sha256,
                    chain_by_id[predecessor.observation_id],
                ):
                    raise GeneratedReferenceChainReplayError(
                        "REFERENCE_ANCHOR_MISMATCH", "predecessor head anchor mismatch"
                    )
                resolved.append(predecessor)
            predecessor_ids[observation.observation_id] = tuple(
                item.observation_id for item in resolved
            )
            if not _transition_valid(observation, tuple(resolved)):
                raise GeneratedReferenceChainReplayError(
                    "IMMEDIATE_LINK_INVALID", "claim transition is outside frozen transition matrix"
                )
        state: dict[str, int] = {}
        ancestors: dict[str, frozenset[str]] = {}

        def visit(observation_id: str) -> frozenset[str]:
            marker = state.get(observation_id, 0)
            if marker == 1:
                raise GeneratedReferenceChainReplayError(
                    "CYCLE_DETECTED", "Observation graph contains a cycle"
                )
            if marker == 2:
                return ancestors[observation_id]
            state[observation_id] = 1
            result: set[str] = set()
            for predecessor_id in predecessor_ids[observation_id]:
                result.add(predecessor_id)
                result.update(visit(predecessor_id))
            state[observation_id] = 2
            ancestors[observation_id] = frozenset(result)
            return ancestors[observation_id]

        for observation_id in ids:
            visit(observation_id)
        genesis = tuple(item for item in observations if item.chain_link.link_kind == "GENESIS")
        if len(genesis) != 1:
            raise GeneratedReferenceChainReplayError(
                "GENESIS_COUNT_INVALID", "logical chain requires exactly one GENESIS"
            )
        genesis_id = genesis[0].observation_id
        if any(
            item.observation_id != genesis_id and genesis_id not in ancestors[item.observation_id]
            for item in observations
        ):
            raise GeneratedReferenceChainReplayError(
                "DISCONNECTED_GRAPH", "an Observation is disconnected from genesis"
            )
        for observation in observations:
            if observation.chain_link.link_kind == "RECONCILIATION":
                heads = predecessor_ids[observation.observation_id]
                if any(
                    left in ancestors[right] or right in ancestors[left]
                    for index, left in enumerate(heads)
                    for right in heads[index + 1 :]
                ):
                    raise GeneratedReferenceChainReplayError(
                        "RECONCILIATION_HEAD_ANCESTRY_CONFLICT",
                        "reconciliation heads must be incomparable",
                    )
        target_ids = tuple(item.observation_id for item in targets)
        if len(target_ids) != len(set(target_ids)):
            raise GeneratedReferenceChainReplayError(
                "REFERENCE_ANCHOR_MISMATCH", "target references must be unique"
            )
        for target in targets:
            target_observation = by_id.get(target.observation_id)
            if target_observation is None or _observation_ref_key(target) != (
                target_observation.observation_id,
                target_observation.observation_sha256,
                chain_by_id[target_observation.observation_id],
            ):
                raise GeneratedReferenceChainReplayError(
                    "REFERENCE_ANCHOR_MISMATCH", "target reference does not resolve exactly"
                )
        relevant: set[str] = set(target_ids)
        for target_id in target_ids:
            relevant.update(ancestors[target_id])
        if relevant != set(ids):
            raise GeneratedReferenceChainReplayError(
                "DISCONNECTED_GRAPH", "explicit chain contains unrelated support Observations"
            )
        occurrences = tuple(
            {
                "observation_id": item.observation_id,
                "observation_sha256": item.observation_sha256,
                "chain_sha256": chain_by_id[item.observation_id],
            }
            for item in sorted(observations, key=lambda item: item.observation_id)
        )
        observation_set_projection = {
            "chain_scope_sha256": next(iter(scopes)),
            "genesis_observation_id": genesis_id,
            "target_observation_refs": _explicit_value(targets),
            "observation_occurrences": list(occurrences),
        }
        observation_set_sha = _semantic_sha256(
            GENERATED_REFERENCE_CURRENT_STATUS_OBSERVATION_SET_SHA256_DOMAIN,
            observation_set_projection,
        )
        return GeneratedReferenceCurrentStatusChainReplayResult(
            chain_scope_sha256=next(iter(scopes)),
            genesis_observation_id=genesis_id,
            observation_set_sha256=observation_set_sha,
            target_observation_refs=targets,
            observation_occurrences=occurrences,
            observations=observations,
            _ancestor_ids_by_observation_id=dict(ancestors),
        )
    except GeneratedReferenceChainReplayError:
        raise
    except Exception as exc:
        raise GeneratedReferenceChainReplayError(
            "INTERNAL_RESULT_INCONSISTENCY", "unexpected chain replay failure"
        ) from exc


def _target_category_result(
    *,
    category: CurrentStatusCategory,
    ordinal: int,
    request: CreativeSampleGeneratedReferenceCurrentStatusRequestV1,
    chain_results: tuple[GeneratedReferenceCurrentStatusChainReplayResult, ...],
    observation_lookup: Mapping[
        str, CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1
    ],
    chain_lookup: Mapping[str, GeneratedReferenceCurrentStatusChainReplayResult],
    evaluated_at: str,
) -> GeneratedReferenceCurrentStatusCategoryResultV1:
    category_refs = tuple(item for item in request.observation_refs if item.category == category)
    evaluated = _parse_utc(evaluated_at, field="evaluated_at")
    relied = tuple(
        ref
        for ref in category_refs
        if observation_lookup[ref.observation_id].claim_value != "NOT_ASSESSED"
        and max(
            _parse_utc(observation_lookup[ref.observation_id].observed_at, field="observed_at"),
            _parse_utc(ref.valid_from, field="valid_from"),
        )
        <= evaluated
        < _parse_utc(ref.valid_until, field="valid_until")
    )
    claims = {observation_lookup[item.observation_id].claim_value for item in relied}
    conflict = len(claims) > 1
    if len(claims) == 1 and len(relied) > 1:
        for index, left in enumerate(relied):
            for right in relied[index + 1 :]:
                left_chain = chain_lookup[left.observation_id]
                right_chain = chain_lookup[right.observation_id]
                comparable = left_chain is right_chain and (
                    left.observation_id
                    in right_chain._ancestor_ids_by_observation_id[right.observation_id]
                    or right.observation_id
                    in left_chain._ancestor_ids_by_observation_id[left.observation_id]
                )
                if comparable:
                    continue
                reconciled = any(
                    chain_lookup[candidate.observation_id] is left_chain is right_chain
                    and left.observation_id
                    in left_chain._ancestor_ids_by_observation_id[candidate.observation_id]
                    and right.observation_id
                    in left_chain._ancestor_ids_by_observation_id[candidate.observation_id]
                    for candidate in relied
                )
                if not reconciled:
                    conflict = True
    if not relied:
        claim: CurrentStatusClaimValue = "NOT_ASSESSED"
    elif conflict:
        claim = "CONFLICT"
    else:
        claim = next(iter(claims))
    result_until_candidates = [
        request.request_valid_until,
        request.subject_closure.manifest_valid_until,
    ]
    result_until_candidates.extend(item.valid_until for item in relied)
    return GeneratedReferenceCurrentStatusCategoryResultV1(
        ordinal=ordinal,
        category=category,
        claim_value=claim,
        deterministic_effect=_derive_effect(category, claim),
        category_observation_refs=category_refs,
        relied_on_observation_refs=relied,
        result_valid_until=min(result_until_candidates),
    )


def _status_preparer_action_projection(
    *,
    actor_identity_ref_sha256: str,
    request: CreativeSampleGeneratedReferenceCurrentStatusRequestV1,
) -> dict[str, object]:
    return {
        "document_profile": (
            "sdc.generated-reference-current-status-request-preparation-action.v1"
        ),
        "action": "PREPARED_GENERATED_REFERENCE_CURRENT_STATUS_REQUEST",
        "actor_identity_ref_sha256": actor_identity_ref_sha256,
        "subject_closure_sha256": request.subject_closure.closure_sha256,
        "policy_document_sha256": request.policy_document_sha256,
        "requested_at": request.requested_at,
        "request_valid_until": request.request_valid_until,
        "observation_target_refs": _explicit_value(request.observation_refs),
        "request_basis": request.request_basis,
    }


def _derive_request_category_results(
    request: CreativeSampleGeneratedReferenceCurrentStatusRequestV1,
    chain_inputs: tuple[GeneratedReferenceCurrentStatusExplicitChainInput, ...],
    *,
    evaluated_at: str,
) -> tuple[GeneratedReferenceCurrentStatusCategoryResultV1, ...]:
    if type(chain_inputs) is not tuple or not 1 <= len(chain_inputs) <= 32:
        _invalid("chain_inputs must be an exact 1..32 item tuple")
    if (
        sum(
            len(item.document_bytes)
            for chain_input in chain_inputs
            for item in chain_input.observation_inputs
        )
        > 16_777_216
    ):
        _invalid("aggregate Observation occurrence bytes exceed 16777216")
    results = tuple(replay_generated_reference_current_status_chain(item) for item in chain_inputs)
    keys = tuple((item.chain_scope_sha256, item.genesis_observation_id) for item in results)
    if keys != tuple(sorted(keys)) or len(keys) != len(set(keys)):
        _invalid("chain_inputs must use unique canonical logical-chain order")
    target_owner: dict[tuple[str, str, str], GeneratedReferenceCurrentStatusChainReplayResult] = {}
    request_keys = tuple(_observation_ref_key(item) for item in request.observation_refs)
    for result in results:
        for target in result.target_observation_refs:
            key = _observation_ref_key(target)
            if key in target_owner:
                _invalid("a Request target is covered more than once")
            if key not in request_keys:
                _invalid("a chain target is not in the exact Request")
            target_owner[key] = result
    if set(target_owner) != set(request_keys):
        _invalid("explicit chains do not cover every and only Request target")
    observations = tuple(item for result in results for item in result.observations)
    ids = tuple(item.observation_id for item in observations)
    document_shas = tuple(item.observation_sha256 for item in observations)
    chain_shas = tuple(
        generated_reference_current_status_chain_sha256(item) for item in observations
    )
    observation_sets = tuple(item.observation_set_sha256 for item in results)
    if any(
        len(values) != len(set(values))
        for values in (ids, document_shas, chain_shas, observation_sets)
    ):
        _invalid("explicit chains violate cross-chain uniqueness")
    observation_lookup = {item.observation_id: item for item in observations}
    chain_lookup = {
        target.observation_id: result
        for result in results
        for target in result.target_observation_refs
    }
    return tuple(
        _target_category_result(
            category=category,
            ordinal=index,
            request=request,
            chain_results=results,
            observation_lookup=observation_lookup,
            chain_lookup=chain_lookup,
            evaluated_at=evaluated_at,
        )
        for index, category in enumerate(CURRENT_STATUS_CATEGORY_ORDER)
    )


def build_generated_reference_current_status_request(
    *,
    subject_closure: GeneratedReferenceCurrentStatusSubjectClosureV1,
    status_preparer_identity_bytes: bytes,
    status_preparer_action_bytes: bytes,
    requested_at: str,
    target_observations: tuple[GeneratedReferenceCurrentStatusObservationInput, ...],
    request_basis: str,
) -> CreativeSampleGeneratedReferenceCurrentStatusRequestV1:
    """Compile canonical Request targets from exact typed Observations and retained action bytes."""

    try:
        closure = cast(
            GeneratedReferenceCurrentStatusSubjectClosureV1,
            _exact_model(
                subject_closure,
                GeneratedReferenceCurrentStatusSubjectClosureV1,
                field="subject_closure",
            ),
        )
        if type(target_observations) is not tuple or not 9 <= len(target_observations) <= 32:
            _invalid("target_observations must be an exact 9..32 item tuple")
        requested_at = _utc_seconds(requested_at, field="requested_at")
        requested = _parse_utc(requested_at, field="requested_at")
        observations = tuple(_admit_observation_input(item) for item in target_observations)
        if any(item.subject_closure != closure for item in observations):
            _invalid("every Request target must bind the exact subject closure")
        if any(
            _parse_utc(item.observed_at, field="observed_at") > requested for item in observations
        ):
            _invalid("a Request target was observed after requested_at")
        refs = tuple(
            generated_reference_current_status_observation_ref(item, ordinal=0)
            for item in observations
        )
        category_index = {
            category: index for index, category in enumerate(CURRENT_STATUS_CATEGORY_ORDER)
        }
        ordered = tuple(
            sorted(
                refs,
                key=lambda item: (
                    category_index[item.category],
                    item.valid_from,
                    item.observation_id,
                ),
            )
        )
        canonical_refs = tuple(
            GeneratedReferenceCurrentStatusObservationRefV1.model_validate(
                {**cast(dict[str, object], _explicit_value(item)), "ordinal": index}
            )
            for index, item in enumerate(ordered)
        )
        valid_until = min(
            requested + timedelta(seconds=86_400),
            _parse_utc(closure.manifest_valid_until, field="manifest_valid_until"),
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        _preparer_identity, preparer_sha = _human_reference(
            status_preparer_identity_bytes, field="Status Preparer identity"
        )
        provisional = _build_generated_reference_current_status_request_contract(
            subject_closure=closure,
            status_preparer_identity_bytes=status_preparer_identity_bytes,
            status_preparer_action_bytes=status_preparer_action_bytes,
            requested_at=requested_at,
            observation_refs=canonical_refs,
            request_basis=request_basis,
        )
        if provisional.request_valid_until != valid_until:
            _invalid("Request validity derivation drift")
        action_sha = _exact_retained_action(
            status_preparer_action_bytes,
            expected=_status_preparer_action_projection(
                actor_identity_ref_sha256=preparer_sha, request=provisional
            ),
            field="Status Preparer action",
        )
        if (
            provisional.status_preparer_identity_ref_sha256 != preparer_sha
            or provisional.status_preparer_action_sha256 != action_sha
        ):
            _invalid("Request retained Preparer anchors mismatch")
        request_forbidden = {
            GENERATED_REFERENCE_CURRENT_STATUS_POLICY_DOCUMENT_SHA256,
            *_collect_sha256_strings(closure),
            *(
                digest
                for observation in observations
                for digest in _collect_sha256_strings(observation)
            ),
        }
        _reject_retained_digest_aliases(
            (preparer_sha, action_sha),
            forbidden=request_forbidden,
            field="Status Request",
        )
        return provisional
    except (TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceRightsCurrentStatusError(
            "REQUEST_CONTRACT_INVALID", "typed Observation Request construction failed"
        ) from exc


def build_generated_reference_current_status_instruction(
    *,
    request: CreativeSampleGeneratedReferenceCurrentStatusRequestV1,
    chain_inputs: tuple[GeneratedReferenceCurrentStatusExplicitChainInput, ...],
    status_preparer_identity_bytes: bytes,
    status_preparer_action_bytes: bytes,
    status_checker_identity_bytes: bytes,
    status_checker_action_bytes: bytes,
    evaluated_at: str,
    checker_basis: str,
) -> CreativeSampleGeneratedReferenceCurrentStatusInstructionV1:
    """Replay exact chains, derive all nine category results, and bind the Checker action."""

    try:
        req = cast(
            CreativeSampleGeneratedReferenceCurrentStatusRequestV1,
            _exact_model(
                request,
                CreativeSampleGeneratedReferenceCurrentStatusRequestV1,
                field="request",
            ),
        )
        preparer_identity, preparer_sha = _human_reference(
            status_preparer_identity_bytes, field="Status Preparer identity"
        )
        if preparer_sha != req.status_preparer_identity_ref_sha256:
            _invalid("Status Preparer identity does not match Request")
        preparer_action_sha = _exact_retained_action(
            status_preparer_action_bytes,
            expected=_status_preparer_action_projection(
                actor_identity_ref_sha256=preparer_sha, request=req
            ),
            field="Status Preparer action",
        )
        if preparer_action_sha != req.status_preparer_action_sha256:
            _invalid("Status Preparer action does not match Request")
        checker_identity, checker_sha = _human_reference(
            status_checker_identity_bytes, field="Status Checker identity"
        )
        preparer_key = (
            preparer_identity["identity_namespace"],
            preparer_identity["identity_ref"],
        )
        checker_key = (
            checker_identity["identity_namespace"],
            checker_identity["identity_ref"],
        )
        if checker_key == preparer_key:
            _invalid("Status Preparer and Checker semantic identities must differ")
        evaluated_at = _utc_seconds(evaluated_at, field="evaluated_at")
        category_results = _derive_request_category_results(
            req, chain_inputs, evaluated_at=evaluated_at
        )
        recorded_status, _revoked, _held, _indeterminate = _derive_status_and_diagnostics(
            category_results
        )
        status_valid_until = min(item.result_valid_until for item in category_results)
        checker_action_document = _admit_retained_json(
            status_checker_action_bytes,
            maximum=262_144,
            field="Status Checker action",
        )
        raw_category_results = checker_action_document.get("category_results")
        if type(raw_category_results) is not list:
            _invalid("Status Checker action category_results must be a JSON array")
        action_category_results = tuple(
            cast(
                GeneratedReferenceCurrentStatusCategoryResultV1,
                _strict_model_from_json_value(
                    item,
                    GeneratedReferenceCurrentStatusCategoryResultV1,
                    field=f"Status Checker action category_results[{index}]",
                ),
            )
            for index, item in enumerate(raw_category_results)
        )
        if action_category_results != category_results:
            _invalid("Status Checker action category_results differ from fresh replay")
        checker_expected = {
            "document_profile": (
                "sdc.generated-reference-current-status-decision-checker-action.v1"
            ),
            "action": "RECORDED_GENERATED_REFERENCE_CURRENT_STATUS_DECISION",
            "actor_identity_ref_sha256": checker_sha,
            "request_sha256": req.request_sha256,
            "evaluated_at": evaluated_at,
            "category_results": _explicit_value(category_results),
            "checker_basis": checker_basis,
            "status_valid_until": status_valid_until,
            "recorded_status": recorded_status,
        }
        checker_action_sha = _exact_retained_action(
            status_checker_action_bytes,
            expected=checker_expected,
            field="Status Checker action",
        )
        _reject_retained_digest_aliases(
            (preparer_sha, preparer_action_sha, checker_sha, checker_action_sha),
            forbidden={
                GENERATED_REFERENCE_CURRENT_STATUS_POLICY_DOCUMENT_SHA256,
                *_collect_sha256_strings(req),
                *(
                    digest
                    for result in category_results
                    for digest in _collect_sha256_strings(result)
                ),
            },
            field="Status Instruction",
        )
        instruction = _build_generated_reference_current_status_instruction_contract(
            request=req,
            status_checker_identity_bytes=status_checker_identity_bytes,
            status_checker_action_bytes=status_checker_action_bytes,
            evaluated_at=evaluated_at,
            category_results=category_results,
            checker_basis=checker_basis,
        )
        if (
            instruction.status_checker_identity_ref_sha256 != checker_sha
            or instruction.status_checker_action_sha256 != checker_action_sha
        ):
            _invalid("Instruction retained Checker anchors mismatch")
        return instruction
    except GeneratedReferenceChainReplayError as exc:
        raise GeneratedReferenceRightsCurrentStatusError(
            "INSTRUCTION_CHAIN_REPLAY_FAILED", "Instruction chain replay failed"
        ) from exc
    except (TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceRightsCurrentStatusError(
            "INSTRUCTION_CONTRACT_INVALID", "Instruction construction failed"
        ) from exc


def build_generated_reference_current_status_decision(
    *,
    request: CreativeSampleGeneratedReferenceCurrentStatusRequestV1,
    instruction: CreativeSampleGeneratedReferenceCurrentStatusInstructionV1,
    chain_inputs: tuple[GeneratedReferenceCurrentStatusExplicitChainInput, ...],
    status_preparer_identity_bytes: bytes,
    status_preparer_action_bytes: bytes,
    status_checker_identity_bytes: bytes,
    status_checker_action_bytes: bytes,
) -> CreativeSampleGeneratedReferenceCurrentStatusDecisionV1:
    rebuilt_instruction = build_generated_reference_current_status_instruction(
        request=request,
        chain_inputs=chain_inputs,
        status_preparer_identity_bytes=status_preparer_identity_bytes,
        status_preparer_action_bytes=status_preparer_action_bytes,
        status_checker_identity_bytes=status_checker_identity_bytes,
        status_checker_action_bytes=status_checker_action_bytes,
        evaluated_at=instruction.evaluated_at,
        checker_basis=instruction.checker_basis,
    )
    if rebuilt_instruction != instruction:
        raise GeneratedReferenceRightsCurrentStatusError(
            "DECISION_CONTRACT_INVALID", "Instruction does not equal fresh chain/action rebuild"
        )
    return _build_generated_reference_current_status_decision_contract(
        request=request, instruction=instruction
    )


def build_generated_reference_current_status_evidence_record(
    *,
    request: CreativeSampleGeneratedReferenceCurrentStatusRequestV1,
    instruction: CreativeSampleGeneratedReferenceCurrentStatusInstructionV1,
    decision: CreativeSampleGeneratedReferenceCurrentStatusDecisionV1,
    chain_inputs: tuple[GeneratedReferenceCurrentStatusExplicitChainInput, ...],
    status_preparer_identity_bytes: bytes,
    status_preparer_action_bytes: bytes,
    status_checker_identity_bytes: bytes,
    status_checker_action_bytes: bytes,
) -> CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1:
    rebuilt_decision = build_generated_reference_current_status_decision(
        request=request,
        instruction=instruction,
        chain_inputs=chain_inputs,
        status_preparer_identity_bytes=status_preparer_identity_bytes,
        status_preparer_action_bytes=status_preparer_action_bytes,
        status_checker_identity_bytes=status_checker_identity_bytes,
        status_checker_action_bytes=status_checker_action_bytes,
    )
    if rebuilt_decision != decision:
        raise GeneratedReferenceRightsCurrentStatusError(
            "EVIDENCE_RECORD_INVALID", "Decision does not equal fresh chain/action rebuild"
        )
    return _build_generated_reference_current_status_evidence_record_contract(
        request=request, instruction=instruction, decision=decision
    )


def cover_generated_reference_current_status_chains(
    record: CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1,
    chain_inputs: tuple[GeneratedReferenceCurrentStatusExplicitChainInput, ...],
) -> GeneratedReferenceCurrentStatusChainCoverageResult:
    try:
        if type(chain_inputs) is not tuple or not 1 <= len(chain_inputs) <= 32:
            raise GeneratedReferenceChainCoverageError(
                "CHAIN_COUNT_OUT_OF_RANGE", "explicit chain count must be 1..32"
            )
        if (
            sum(
                len(item.document_bytes)
                for chain_input in chain_inputs
                for item in chain_input.observation_inputs
            )
            > 16_777_216
        ):
            raise GeneratedReferenceChainCoverageError(
                "AGGREGATE_CANONICAL_BYTES_OUT_OF_RANGE",
                "aggregate Observation occurrence bytes exceed 16777216",
            )
        try:
            validated_record = cast(
                CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1,
                _exact_model(
                    record,
                    CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1,
                    field="record",
                ),
            )
        except (TypeError, ValueError, ValidationError) as exc:
            raise GeneratedReferenceChainCoverageError(
                "EVIDENCE_RECORD_INVALID", "Evidence Record is invalid"
            ) from exc
        results: list[GeneratedReferenceCurrentStatusChainReplayResult] = []
        for chain_input in chain_inputs:
            try:
                results.append(replay_generated_reference_current_status_chain(chain_input))
            except GeneratedReferenceChainReplayError as exc:
                raise GeneratedReferenceChainCoverageError(
                    "CHAIN_REPLAY_FAILED",
                    "one explicit logical chain failed replay",
                    replay_code=exc.code,
                ) from exc
        chain_results = tuple(results)
        logical_keys = tuple(
            (item.chain_scope_sha256, item.genesis_observation_id) for item in chain_results
        )
        if logical_keys != tuple(sorted(logical_keys)):
            raise GeneratedReferenceChainCoverageError(
                "CHAIN_COLLECTION_CONTRACT_INVALID",
                "logical chain inputs are not in canonical key order",
            )
        if len(logical_keys) != len(set(logical_keys)):
            raise GeneratedReferenceChainCoverageError(
                "DUPLICATE_LOGICAL_CHAIN", "duplicate logical-chain key"
            )
        all_observations = tuple(
            observation for result in chain_results for observation in result.observations
        )
        all_ids = tuple(item.observation_id for item in all_observations)
        all_document_shas = tuple(item.observation_sha256 for item in all_observations)
        all_chain_shas = tuple(
            generated_reference_current_status_chain_sha256(item) for item in all_observations
        )
        for values, code in (
            (all_ids, "CROSS_CHAIN_DUPLICATE_OBSERVATION_ID"),
            (all_document_shas, "CROSS_CHAIN_DUPLICATE_OBSERVATION_DOCUMENT_SHA256"),
            (all_chain_shas, "CROSS_CHAIN_DUPLICATE_OBSERVATION_CHAIN_SHA256"),
            (
                tuple(item.observation_set_sha256 for item in chain_results),
                "CROSS_CHAIN_DUPLICATE_OBSERVATION_SET_SHA256",
            ),
        ):
            if len(values) != len(set(values)):
                raise GeneratedReferenceChainCoverageError(
                    code, "cross-chain uniqueness constraint failed"
                )
        request_targets = validated_record.request.observation_refs
        request_keys = tuple(_observation_ref_key(item) for item in request_targets)
        target_owner: dict[
            tuple[str, str, str], GeneratedReferenceCurrentStatusChainReplayResult
        ] = {}
        for result in chain_results:
            for target in result.target_observation_refs:
                key = _observation_ref_key(target)
                if key in target_owner:
                    raise GeneratedReferenceChainCoverageError(
                        "REQUEST_TARGET_COVERED_MULTIPLE_TIMES",
                        "Request target is covered more than once",
                    )
                if key not in request_keys:
                    raise GeneratedReferenceChainCoverageError(
                        "REQUEST_TARGET_NOT_IN_RECORD",
                        "chain target is not an explicit Request target",
                    )
                target_owner[key] = result
        if set(target_owner) != set(request_keys):
            raise GeneratedReferenceChainCoverageError(
                "REQUEST_OBSERVATION_NOT_COVERED", "not every explicit Request target is covered"
            )
        target_coverage = tuple(
            {
                "target_observation_ref": _explicit_value(target),
                "chain_scope_sha256": target_owner[_observation_ref_key(target)].chain_scope_sha256,
                "genesis_observation_id": target_owner[
                    _observation_ref_key(target)
                ].genesis_observation_id,
                "observation_set_sha256": target_owner[
                    _observation_ref_key(target)
                ].observation_set_sha256,
            }
            for target in request_targets
        )
        chain_members = tuple(
            {
                "chain_scope_sha256": result.chain_scope_sha256,
                "genesis_observation_id": result.genesis_observation_id,
                "observation_set_sha256": result.observation_set_sha256,
                "target_observation_refs": _explicit_value(result.target_observation_refs),
            }
            for result in chain_results
        )
        explicit_projection = {
            "policy_document_sha256": GENERATED_REFERENCE_CURRENT_STATUS_POLICY_DOCUMENT_SHA256,
            "subject_closure_id": validated_record.subject_closure.closure_id,
            "subject_closure_sha256": validated_record.subject_closure.closure_sha256,
            "request_id": validated_record.request.request_id,
            "request_sha256": validated_record.request.request_sha256,
            "chain_inputs": list(chain_members),
        }
        explicit_sha = _semantic_sha256(
            GENERATED_REFERENCE_CURRENT_STATUS_EXPLICIT_CHAIN_SET_SHA256_DOMAIN, explicit_projection
        )
        coverage_projection = {
            "record_id": validated_record.record_id,
            "record_sha256": validated_record.record_sha256,
            "request_id": validated_record.request.request_id,
            "request_sha256": validated_record.request.request_sha256,
            "subject_closure_sha256": validated_record.subject_closure.closure_sha256,
            "explicit_chain_set_sha256": explicit_sha,
            "target_coverage": list(target_coverage),
        }
        coverage_sha = _semantic_sha256(
            GENERATED_REFERENCE_CURRENT_STATUS_COVERAGE_SET_SHA256_DOMAIN, coverage_projection
        )
        observation_lookup = {item.observation_id: item for item in all_observations}
        chain_lookup = {
            target.observation_id: result
            for result in chain_results
            for target in result.target_observation_refs
        }
        category_results = tuple(
            _target_category_result(
                category=category,
                ordinal=index,
                request=validated_record.request,
                chain_results=chain_results,
                observation_lookup=observation_lookup,
                chain_lookup=chain_lookup,
                evaluated_at=validated_record.instruction.evaluated_at,
            )
            for index, category in enumerate(CURRENT_STATUS_CATEGORY_ORDER)
        )
        if (
            category_results != validated_record.instruction.category_results
            or category_results != validated_record.decision.category_results
        ):
            raise GeneratedReferenceChainCoverageError(
                "RECORD_REBUILD_MISMATCH", "fresh replay category results differ from Record"
            )
        return GeneratedReferenceCurrentStatusChainCoverageResult(
            explicit_chain_set_sha256=explicit_sha,
            coverage_set_sha256=coverage_sha,
            chain_results=chain_results,
            target_coverage=target_coverage,
            category_results=category_results,
        )
    except GeneratedReferenceChainCoverageError:
        raise
    except Exception as exc:
        raise GeneratedReferenceChainCoverageError(
            "INTERNAL_RESULT_INCONSISTENCY", "unexpected coverage failure"
        ) from exc


def jointly_replay_generated_reference_current_status_record(
    record: CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1,
    manifest: CreativeSampleGeneratedReferenceRightsManifestV1,
    chain_inputs: tuple[GeneratedReferenceCurrentStatusExplicitChainInput, ...],
) -> GeneratedReferenceCurrentStatusJointReplayResult:
    try:
        try:
            validated_record = cast(
                CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1,
                _exact_model(
                    record,
                    CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1,
                    field="record",
                ),
            )
            validated_manifest = cast(
                CreativeSampleGeneratedReferenceRightsManifestV1,
                _exact_model(
                    manifest,
                    CreativeSampleGeneratedReferenceRightsManifestV1,
                    field="manifest",
                ),
            )
        except (
            GeneratedReferenceRightsCurrentStatusError,
            TypeError,
            ValueError,
            ValidationError,
        ) as exc:
            raise GeneratedReferenceJointReplayError(
                "PROVIDED_OBJECT_CLOSURE_REPLAY_FAILED", "Record or Manifest contract failed"
            ) from exc
        expected_closure = build_generated_reference_current_status_subject_closure(
            validated_manifest
        )
        if validated_record.subject_closure != expected_closure:
            raise GeneratedReferenceJointReplayError(
                "PROVIDED_OBJECT_CLOSURE_REPLAY_FAILED",
                "Record does not bind exact Manifest subject closure",
            )
        try:
            coverage = cover_generated_reference_current_status_chains(
                validated_record, chain_inputs
            )
        except GeneratedReferenceChainCoverageError as exc:
            raise GeneratedReferenceJointReplayError(
                "RECORD_CHAIN_COVERAGE_REPLAY_FAILED",
                "chain coverage failed",
                coverage_code=exc.code,
                replay_code=exc.replay_code,
            ) from exc
        recorded_status, revoked, held, indeterminate = _derive_status_and_diagnostics(
            coverage.category_results
        )
        decision = validated_record.decision
        if (recorded_status, revoked, held, indeterminate) != (
            decision.recorded_status,
            decision.revoked_categories,
            decision.held_categories,
            decision.indeterminate_categories,
        ):
            raise GeneratedReferenceJointReplayError(
                "TARGET_OBSERVATION_DERIVATION_INCONSISTENT",
                "fresh resolver output differs from Decision",
            )
        projection = {
            "record_id": validated_record.record_id,
            "record_sha256": validated_record.record_sha256,
            "subject_closure_id": validated_record.subject_closure.closure_id,
            "subject_closure_sha256": validated_record.subject_closure.closure_sha256,
            "explicit_chain_set_sha256": coverage.explicit_chain_set_sha256,
            "coverage_set_sha256": coverage.coverage_set_sha256,
            "request_id": validated_record.request.request_id,
            "request_sha256": validated_record.request.request_sha256,
            "instruction_id": validated_record.instruction.instruction_id,
            "instruction_sha256": validated_record.instruction.instruction_sha256,
            "decision_id": decision.decision_id,
            "decision_sha256": decision.decision_sha256,
            "category_results": _explicit_value(coverage.category_results),
            "recorded_status": recorded_status,
        }
        joint_sha = _semantic_sha256(
            GENERATED_REFERENCE_CURRENT_STATUS_JOINT_REPLAY_SHA256_DOMAIN, projection
        )
        return GeneratedReferenceCurrentStatusJointReplayResult(
            explicit_chain_set_sha256=coverage.explicit_chain_set_sha256,
            coverage_set_sha256=coverage.coverage_set_sha256,
            joint_replay_sha256=joint_sha,
            category_results=coverage.category_results,
            recorded_status=recorded_status,
            _coverage=coverage,
        )
    except GeneratedReferenceJointReplayError:
        raise
    except Exception as exc:
        raise GeneratedReferenceJointReplayError(
            "INTERNAL_RESULT_INCONSISTENCY", "unexpected joint replay failure"
        ) from exc


def _as_of_projection(
    *,
    record: CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1,
    joint: GeneratedReferenceCurrentStatusJointReplayResult,
    as_of: str,
    as_of_status: CurrentStatusResult,
) -> dict[str, object]:
    decision = record.decision
    return {
        "record_id": record.record_id,
        "record_sha256": record.record_sha256,
        "decision_id": decision.decision_id,
        "decision_sha256": decision.decision_sha256,
        "subject_closure_id": record.subject_closure.closure_id,
        "subject_closure_sha256": record.subject_closure.closure_sha256,
        "joint_replay_sha256": joint.joint_replay_sha256,
        "as_of": as_of,
        "evaluated_at": decision.evaluated_at,
        "status_valid_until": decision.status_valid_until,
        "manifest_valid_until": record.subject_closure.manifest_valid_until,
        "recorded_status": decision.recorded_status,
        "as_of_status": as_of_status,
        "recorded_revoked_categories": list(decision.revoked_categories),
        "recorded_held_categories": list(decision.held_categories),
        "recorded_indeterminate_categories": list(decision.indeterminate_categories),
        "limitation_codes": list(CURRENT_STATUS_LIMITATION_CODE_ORDER),
        "present_currentness_asserted": False,
        "evidence_scope": "EXPLICIT_FINITE_BOUND_SET_ONLY",
        **_zero_authority_values(),
    }


def assess_generated_reference_current_status_record_as_of(
    record: CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1,
    manifest: CreativeSampleGeneratedReferenceRightsManifestV1,
    chain_inputs: tuple[GeneratedReferenceCurrentStatusExplicitChainInput, ...],
    *,
    as_of: str,
) -> GeneratedReferenceCurrentStatusAsOfAssessmentResult:
    try:
        try:
            as_of_dt = _parse_utc(as_of, field="as_of")
        except ValueError as exc:
            raise GeneratedReferenceAsOfAssessmentError(
                "AS_OF_CONTRACT_INVALID", "as_of must be canonical UTC seconds"
            ) from exc
        try:
            validated_record = cast(
                CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1,
                _exact_model(
                    record,
                    CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1,
                    field="record",
                ),
            )
            joint = jointly_replay_generated_reference_current_status_record(
                validated_record, manifest, chain_inputs
            )
        except GeneratedReferenceJointReplayError as exc:
            raise GeneratedReferenceAsOfAssessmentError(
                "RECORD_JOINT_REPLAY_FAILED",
                "joint replay failed",
                joint_replay_code=exc.code,
                coverage_code=exc.coverage_code,
                replay_code=exc.replay_code,
            ) from exc
        evaluated = _parse_utc(validated_record.decision.evaluated_at, field="evaluated_at")
        if as_of_dt < evaluated:
            raise GeneratedReferenceAsOfAssessmentError(
                "AS_OF_PRECEDES_RECORD_EVALUATION", "as_of cannot precede evaluated_at"
            )
        expired = as_of_dt >= _parse_utc(
            validated_record.decision.status_valid_until, field="status_valid_until"
        ) or as_of_dt >= _parse_utc(
            validated_record.subject_closure.manifest_valid_until, field="manifest_valid_until"
        )
        as_of_status: CurrentStatusResult = (
            "EXPIRED" if expired else validated_record.decision.recorded_status
        )
        projection = _as_of_projection(
            record=validated_record, joint=joint, as_of=as_of, as_of_status=as_of_status
        )
        assessment_sha = _semantic_sha256(
            GENERATED_REFERENCE_CURRENT_STATUS_RECORD_AS_OF_ASSESSMENT_SHA256_DOMAIN, projection
        )
        provenance_projection = {
            "as_of_assessment_sha256": assessment_sha,
            "explicit_chain_set_sha256": joint.explicit_chain_set_sha256,
            "coverage_set_sha256": joint.coverage_set_sha256,
            "joint_replay_sha256": joint.joint_replay_sha256,
            "record_id": validated_record.record_id,
            "record_sha256": validated_record.record_sha256,
        }
        provenance_sha = _semantic_sha256(
            GENERATED_REFERENCE_CURRENT_STATUS_RECORD_AS_OF_ASSESSMENT_PROVENANCE_SHA256_DOMAIN,
            provenance_projection,
        )
        return GeneratedReferenceCurrentStatusAsOfAssessmentResult(
            record_id=validated_record.record_id,
            record_sha256=validated_record.record_sha256,
            request_id=validated_record.request.request_id,
            request_sha256=validated_record.request.request_sha256,
            decision_id=validated_record.decision.decision_id,
            decision_sha256=validated_record.decision.decision_sha256,
            subject_closure=validated_record.subject_closure,
            explicit_chain_set_sha256=joint.explicit_chain_set_sha256,
            coverage_set_sha256=joint.coverage_set_sha256,
            joint_replay_sha256=joint.joint_replay_sha256,
            as_of_assessment_sha256=assessment_sha,
            as_of=as_of,
            evaluated_at=validated_record.decision.evaluated_at,
            status_valid_until=validated_record.decision.status_valid_until,
            recorded_status=validated_record.decision.recorded_status,
            as_of_status=as_of_status,
            recorded_revoked_categories=validated_record.decision.revoked_categories,
            recorded_held_categories=validated_record.decision.held_categories,
            recorded_indeterminate_categories=validated_record.decision.indeterminate_categories,
            limitation_codes=CURRENT_STATUS_LIMITATION_CODE_ORDER,
            _provenance_sha256=provenance_sha,
            _guard=_ASSESSMENT_GUARD,
        )
    except GeneratedReferenceAsOfAssessmentError:
        raise
    except Exception as exc:
        raise GeneratedReferenceAsOfAssessmentError(
            "INTERNAL_RESULT_INCONSISTENCY", "unexpected as-of assessment failure"
        ) from exc


def build_generated_reference_current_status_record_as_of_assessment_receipt(
    assessment: GeneratedReferenceCurrentStatusAsOfAssessmentResult,
) -> CreativeSampleGeneratedReferenceCurrentStatusRecordAsOfAssessmentReceiptV1:
    try:
        if (
            type(assessment) is not GeneratedReferenceCurrentStatusAsOfAssessmentResult
            or assessment._guard is not _ASSESSMENT_GUARD
        ):
            raise GeneratedReferenceReceiptError(
                "ASSESSMENT_RESULT_INCONSISTENT",
                "Receipt requires the exact same-call private assessment Result",
            )
        provenance_projection = {
            "as_of_assessment_sha256": assessment.as_of_assessment_sha256,
            "explicit_chain_set_sha256": assessment.explicit_chain_set_sha256,
            "coverage_set_sha256": assessment.coverage_set_sha256,
            "joint_replay_sha256": assessment.joint_replay_sha256,
            "record_id": assessment.record_id,
            "record_sha256": assessment.record_sha256,
        }
        expected_provenance = _semantic_sha256(
            GENERATED_REFERENCE_CURRENT_STATUS_RECORD_AS_OF_ASSESSMENT_PROVENANCE_SHA256_DOMAIN,
            provenance_projection,
        )
        if assessment._provenance_sha256 != expected_provenance:
            raise GeneratedReferenceReceiptError(
                "ASSESSMENT_RESULT_INCONSISTENT", "private assessment provenance mismatch"
            )
        values = {
            **_base_current_values(),
            "document_type": (
                "sdc.creative-sample-generated-reference-current-status-"
                "record-as-of-assessment-receipt-v1"
            ),
            "receipt_scope": "GENERATED_REFERENCE_CURRENT_STATUS_HISTORICAL_AS_OF_EVIDENCE_ONLY",
            "record_id": assessment.record_id,
            "record_sha256": assessment.record_sha256,
            "request_id": assessment.request_id,
            "request_sha256": assessment.request_sha256,
            "decision_id": assessment.decision_id,
            "decision_sha256": assessment.decision_sha256,
            "subject_closure": assessment.subject_closure,
            "explicit_chain_set_sha256": assessment.explicit_chain_set_sha256,
            "coverage_set_sha256": assessment.coverage_set_sha256,
            "joint_replay_sha256": assessment.joint_replay_sha256,
            "as_of_assessment_sha256": assessment.as_of_assessment_sha256,
            "as_of": assessment.as_of,
            "evaluated_at": assessment.evaluated_at,
            "status_valid_until": assessment.status_valid_until,
            "window_semantics": "EVALUATED_AT_INCLUSIVE_STATUS_VALID_UNTIL_EXCLUSIVE",
            "recorded_status": assessment.recorded_status,
            "as_of_status": assessment.as_of_status,
            "recorded_revoked_categories": assessment.recorded_revoked_categories,
            "recorded_held_categories": assessment.recorded_held_categories,
            "recorded_indeterminate_categories": assessment.recorded_indeterminate_categories,
            "record_replay_consistent": True,
            "same_call_assessment_verified": True,
            "historical_assessment_only": True,
            "present_currentness_asserted": False,
            "limitation_codes": assessment.limitation_codes,
            "status": "GENERATED_CURRENT_STATUS_AS_OF_RECEIPT_RECORDED",
        }
        return cast(
            CreativeSampleGeneratedReferenceCurrentStatusRecordAsOfAssessmentReceiptV1,
            _build_identity_contract(
                CreativeSampleGeneratedReferenceCurrentStatusRecordAsOfAssessmentReceiptV1,
                values=values,
                id_field="receipt_id",
                sha_field="receipt_sha256",
                stem="generated_reference_current_status_record_as_of_assessment_receipt_v1_",
                domain=GENERATED_REFERENCE_CURRENT_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_SHA256_DOMAIN,
            ),
        )
    except GeneratedReferenceReceiptError:
        raise
    except (TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceReceiptError(
            "INTERNAL_RECEIPT_INCONSISTENCY", "Receipt construction failed"
        ) from exc


def verify_generated_reference_current_status_record_as_of_assessment_receipt(
    receipt: CreativeSampleGeneratedReferenceCurrentStatusRecordAsOfAssessmentReceiptV1,
    *,
    record: CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1 | None = None,
    manifest: CreativeSampleGeneratedReferenceRightsManifestV1 | None = None,
    chain_inputs: tuple[GeneratedReferenceCurrentStatusExplicitChainInput, ...] | None = None,
) -> CreativeSampleGeneratedReferenceCurrentStatusRecordAsOfAssessmentReceiptV1:
    try:
        try:
            validated = cast(
                CreativeSampleGeneratedReferenceCurrentStatusRecordAsOfAssessmentReceiptV1,
                _exact_model(
                    receipt,
                    CreativeSampleGeneratedReferenceCurrentStatusRecordAsOfAssessmentReceiptV1,
                    field="receipt",
                ),
            )
        except (TypeError, ValueError, ValidationError) as exc:
            raise GeneratedReferenceReceiptError(
                "RECEIPT_CONTRACT_INVALID", "Receipt Contract is invalid"
            ) from exc
        supplied = (record is not None, manifest is not None, chain_inputs is not None)
        if any(supplied) and not all(supplied):
            raise GeneratedReferenceReceiptError(
                "RECEIPT_REPLAY_MISMATCH",
                "full replay requires Record, Manifest and explicit chain inputs together",
            )
        if all(supplied):
            try:
                assessment = assess_generated_reference_current_status_record_as_of(
                    cast(CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1, record),
                    cast(CreativeSampleGeneratedReferenceRightsManifestV1, manifest),
                    cast(
                        tuple[GeneratedReferenceCurrentStatusExplicitChainInput, ...], chain_inputs
                    ),
                    as_of=validated.as_of,
                )
                rebuilt = build_generated_reference_current_status_record_as_of_assessment_receipt(
                    assessment
                )
            except GeneratedReferenceAsOfAssessmentError as exc:
                raise GeneratedReferenceReceiptError(
                    "AS_OF_ASSESSMENT_REPLAY_FAILED",
                    "Receipt replay assessment failed",
                    assessment_code=exc.code,
                    joint_replay_code=exc.joint_replay_code,
                    coverage_code=exc.coverage_code,
                    replay_code=exc.replay_code,
                ) from exc
            if rebuilt != validated:
                raise GeneratedReferenceReceiptError(
                    "RECEIPT_REPLAY_MISMATCH",
                    "fresh same-call Receipt differs from supplied Receipt",
                )
        return validated
    except GeneratedReferenceReceiptError:
        raise
    except Exception as exc:
        raise GeneratedReferenceReceiptError(
            "INTERNAL_RECEIPT_INCONSISTENCY", "unexpected Receipt verification failure"
        ) from exc


@dataclass(frozen=True, slots=True)
class GeneratedReferenceCurrentStatusReceiptProcessResult:
    assessment: GeneratedReferenceCurrentStatusAsOfAssessmentResult
    receipt: CreativeSampleGeneratedReferenceCurrentStatusRecordAsOfAssessmentReceiptV1


def process_generated_reference_current_status_record_as_of_assessment(
    record: CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1,
    manifest: CreativeSampleGeneratedReferenceRightsManifestV1,
    chain_inputs: tuple[GeneratedReferenceCurrentStatusExplicitChainInput, ...],
    *,
    as_of: str,
) -> GeneratedReferenceCurrentStatusReceiptProcessResult:
    try:
        assessment = assess_generated_reference_current_status_record_as_of(
            record, manifest, chain_inputs, as_of=as_of
        )
        receipt = build_generated_reference_current_status_record_as_of_assessment_receipt(
            assessment
        )
        verify_generated_reference_current_status_record_as_of_assessment_receipt(
            receipt, record=record, manifest=manifest, chain_inputs=chain_inputs
        )
        return GeneratedReferenceCurrentStatusReceiptProcessResult(
            assessment=assessment, receipt=receipt
        )
    except GeneratedReferenceReceiptError:
        raise
    except GeneratedReferenceAsOfAssessmentError as exc:
        raise GeneratedReferenceReceiptError(
            "AS_OF_ASSESSMENT_REPLAY_FAILED",
            "as-of process failed",
            assessment_code=exc.code,
            joint_replay_code=exc.joint_replay_code,
            coverage_code=exc.coverage_code,
            replay_code=exc.replay_code,
        ) from exc


def generated_reference_current_status_observation_set_projection(
    result: GeneratedReferenceCurrentStatusChainReplayResult,
) -> dict[str, object]:
    if type(result) is not GeneratedReferenceCurrentStatusChainReplayResult:
        _invalid("result must have exact ChainReplayResult process type")
    return {
        "chain_scope_sha256": result.chain_scope_sha256,
        "genesis_observation_id": result.genesis_observation_id,
        "target_observation_refs": _explicit_value(result.target_observation_refs),
        "observation_occurrences": list(result.observation_occurrences),
    }


def generated_reference_current_status_observation_set_sha256(
    result: GeneratedReferenceCurrentStatusChainReplayResult,
) -> str:
    digest = _semantic_sha256(
        GENERATED_REFERENCE_CURRENT_STATUS_OBSERVATION_SET_SHA256_DOMAIN,
        generated_reference_current_status_observation_set_projection(result),
    )
    if digest != result.observation_set_sha256:
        _invalid("ChainReplayResult observation-set digest mismatch")
    return digest


def generated_reference_current_status_explicit_chain_set_projection(
    record: CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1,
    coverage: GeneratedReferenceCurrentStatusChainCoverageResult,
) -> dict[str, object]:
    validated = cast(
        CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1,
        _exact_model(
            record,
            CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1,
            field="record",
        ),
    )
    if type(coverage) is not GeneratedReferenceCurrentStatusChainCoverageResult:
        _invalid("coverage must have exact ChainCoverageResult process type")
    return {
        "policy_document_sha256": GENERATED_REFERENCE_CURRENT_STATUS_POLICY_DOCUMENT_SHA256,
        "subject_closure_id": validated.subject_closure.closure_id,
        "subject_closure_sha256": validated.subject_closure.closure_sha256,
        "request_id": validated.request.request_id,
        "request_sha256": validated.request.request_sha256,
        "chain_inputs": [
            {
                "chain_scope_sha256": result.chain_scope_sha256,
                "genesis_observation_id": result.genesis_observation_id,
                "observation_set_sha256": result.observation_set_sha256,
                "target_observation_refs": _explicit_value(result.target_observation_refs),
            }
            for result in coverage.chain_results
        ],
    }


def generated_reference_current_status_explicit_chain_set_sha256(
    record: CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1,
    coverage: GeneratedReferenceCurrentStatusChainCoverageResult,
) -> str:
    digest = _semantic_sha256(
        GENERATED_REFERENCE_CURRENT_STATUS_EXPLICIT_CHAIN_SET_SHA256_DOMAIN,
        generated_reference_current_status_explicit_chain_set_projection(record, coverage),
    )
    if digest != coverage.explicit_chain_set_sha256:
        _invalid("ChainCoverageResult explicit-chain-set digest mismatch")
    return digest


def generated_reference_current_status_coverage_set_projection(
    record: CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1,
    coverage: GeneratedReferenceCurrentStatusChainCoverageResult,
) -> dict[str, object]:
    validated = cast(
        CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1,
        _exact_model(
            record,
            CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1,
            field="record",
        ),
    )
    generated_reference_current_status_explicit_chain_set_sha256(validated, coverage)
    return {
        "record_id": validated.record_id,
        "record_sha256": validated.record_sha256,
        "request_id": validated.request.request_id,
        "request_sha256": validated.request.request_sha256,
        "subject_closure_sha256": validated.subject_closure.closure_sha256,
        "explicit_chain_set_sha256": coverage.explicit_chain_set_sha256,
        "target_coverage": list(coverage.target_coverage),
    }


def generated_reference_current_status_coverage_set_sha256(
    record: CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1,
    coverage: GeneratedReferenceCurrentStatusChainCoverageResult,
) -> str:
    digest = _semantic_sha256(
        GENERATED_REFERENCE_CURRENT_STATUS_COVERAGE_SET_SHA256_DOMAIN,
        generated_reference_current_status_coverage_set_projection(record, coverage),
    )
    if digest != coverage.coverage_set_sha256:
        _invalid("ChainCoverageResult coverage-set digest mismatch")
    return digest


def generated_reference_current_status_joint_replay_projection(
    record: CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1,
    result: GeneratedReferenceCurrentStatusJointReplayResult,
) -> dict[str, object]:
    validated = cast(
        CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1,
        _exact_model(
            record,
            CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1,
            field="record",
        ),
    )
    if type(result) is not GeneratedReferenceCurrentStatusJointReplayResult:
        _invalid("result must have exact JointReplayResult process type")
    return {
        "record_id": validated.record_id,
        "record_sha256": validated.record_sha256,
        "subject_closure_id": validated.subject_closure.closure_id,
        "subject_closure_sha256": validated.subject_closure.closure_sha256,
        "explicit_chain_set_sha256": result.explicit_chain_set_sha256,
        "coverage_set_sha256": result.coverage_set_sha256,
        "request_id": validated.request.request_id,
        "request_sha256": validated.request.request_sha256,
        "instruction_id": validated.instruction.instruction_id,
        "instruction_sha256": validated.instruction.instruction_sha256,
        "decision_id": validated.decision.decision_id,
        "decision_sha256": validated.decision.decision_sha256,
        "category_results": _explicit_value(result.category_results),
        "recorded_status": result.recorded_status,
    }


def generated_reference_current_status_joint_replay_sha256(
    record: CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1,
    result: GeneratedReferenceCurrentStatusJointReplayResult,
) -> str:
    digest = _semantic_sha256(
        GENERATED_REFERENCE_CURRENT_STATUS_JOINT_REPLAY_SHA256_DOMAIN,
        generated_reference_current_status_joint_replay_projection(record, result),
    )
    if digest != result.joint_replay_sha256:
        _invalid("JointReplayResult digest mismatch")
    return digest


def generated_reference_current_status_record_as_of_assessment_projection(
    result: GeneratedReferenceCurrentStatusAsOfAssessmentResult,
) -> dict[str, object]:
    if type(result) is not GeneratedReferenceCurrentStatusAsOfAssessmentResult:
        _invalid("result must have exact AsOfAssessmentResult process type")
    return {
        "record_id": result.record_id,
        "record_sha256": result.record_sha256,
        "decision_id": result.decision_id,
        "decision_sha256": result.decision_sha256,
        "subject_closure_id": result.subject_closure.closure_id,
        "subject_closure_sha256": result.subject_closure.closure_sha256,
        "joint_replay_sha256": result.joint_replay_sha256,
        "as_of": result.as_of,
        "evaluated_at": result.evaluated_at,
        "status_valid_until": result.status_valid_until,
        "manifest_valid_until": result.subject_closure.manifest_valid_until,
        "recorded_status": result.recorded_status,
        "as_of_status": result.as_of_status,
        "recorded_revoked_categories": list(result.recorded_revoked_categories),
        "recorded_held_categories": list(result.recorded_held_categories),
        "recorded_indeterminate_categories": list(result.recorded_indeterminate_categories),
        "limitation_codes": list(result.limitation_codes),
        "present_currentness_asserted": False,
        "evidence_scope": "EXPLICIT_FINITE_BOUND_SET_ONLY",
        **_zero_authority_values(),
    }


def generated_reference_current_status_record_as_of_assessment_sha256(
    result: GeneratedReferenceCurrentStatusAsOfAssessmentResult,
) -> str:
    digest = _semantic_sha256(
        GENERATED_REFERENCE_CURRENT_STATUS_RECORD_AS_OF_ASSESSMENT_SHA256_DOMAIN,
        generated_reference_current_status_record_as_of_assessment_projection(result),
    )
    if digest != result.as_of_assessment_sha256:
        _invalid("AsOfAssessmentResult digest mismatch")
    return digest


def verify_generated_reference_current_status_source_observation(
    value: CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1,
    *,
    source_identity_bytes: bytes,
    source_object_bytes: bytes,
) -> CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1:
    validated = cast(
        CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1,
        _exact_model(
            value,
            CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1,
            field="observation",
        ),
    )
    rebuilt = build_generated_reference_current_status_source_observation(
        subject_closure=validated.subject_closure,
        category=validated.category,
        claim_value=validated.claim_value,
        source_kind=validated.source_kind,
        basis_code=validated.basis_code,
        basis_note=validated.basis_note,
        source_identity_bytes=source_identity_bytes,
        source_object_ref=validated.source_object_ref,
        source_object_bytes=source_object_bytes,
        source_object_media_type=validated.source_object_media_type,
        source_event_at=validated.source_event_at,
        observed_at=validated.observed_at,
        valid_from=validated.valid_from,
        valid_until=validated.valid_until,
        link_kind=validated.chain_link.link_kind,
        predecessor_heads=validated.chain_link.predecessor_heads,
    )
    if rebuilt != validated:
        _invalid("Source Observation differs from exact retained-byte rebuild")
    return validated


def verify_generated_reference_current_status_request(
    value: CreativeSampleGeneratedReferenceCurrentStatusRequestV1,
    *,
    status_preparer_identity_bytes: bytes,
    status_preparer_action_bytes: bytes,
    target_observations: tuple[GeneratedReferenceCurrentStatusObservationInput, ...],
) -> CreativeSampleGeneratedReferenceCurrentStatusRequestV1:
    validated = cast(
        CreativeSampleGeneratedReferenceCurrentStatusRequestV1,
        _exact_model(
            value, CreativeSampleGeneratedReferenceCurrentStatusRequestV1, field="request"
        ),
    )
    rebuilt = build_generated_reference_current_status_request(
        subject_closure=validated.subject_closure,
        status_preparer_identity_bytes=status_preparer_identity_bytes,
        status_preparer_action_bytes=status_preparer_action_bytes,
        requested_at=validated.requested_at,
        target_observations=target_observations,
        request_basis=validated.request_basis,
    )
    if rebuilt != validated:
        _invalid("Request differs from exact retained-byte/Observation rebuild")
    return validated


def verify_generated_reference_current_status_instruction(
    value: CreativeSampleGeneratedReferenceCurrentStatusInstructionV1,
    *,
    request: CreativeSampleGeneratedReferenceCurrentStatusRequestV1,
    chain_inputs: tuple[GeneratedReferenceCurrentStatusExplicitChainInput, ...],
    status_preparer_identity_bytes: bytes,
    status_preparer_action_bytes: bytes,
    status_checker_identity_bytes: bytes,
    status_checker_action_bytes: bytes,
) -> CreativeSampleGeneratedReferenceCurrentStatusInstructionV1:
    validated = cast(
        CreativeSampleGeneratedReferenceCurrentStatusInstructionV1,
        _exact_model(
            value, CreativeSampleGeneratedReferenceCurrentStatusInstructionV1, field="instruction"
        ),
    )
    rebuilt = build_generated_reference_current_status_instruction(
        request=request,
        chain_inputs=chain_inputs,
        status_preparer_identity_bytes=status_preparer_identity_bytes,
        status_preparer_action_bytes=status_preparer_action_bytes,
        status_checker_identity_bytes=status_checker_identity_bytes,
        status_checker_action_bytes=status_checker_action_bytes,
        evaluated_at=validated.evaluated_at,
        checker_basis=validated.checker_basis,
    )
    if rebuilt != validated:
        _invalid("Instruction differs from fresh replay/action rebuild")
    return validated


def verify_generated_reference_current_status_decision(
    value: CreativeSampleGeneratedReferenceCurrentStatusDecisionV1,
    *,
    request: CreativeSampleGeneratedReferenceCurrentStatusRequestV1,
    instruction: CreativeSampleGeneratedReferenceCurrentStatusInstructionV1,
    chain_inputs: tuple[GeneratedReferenceCurrentStatusExplicitChainInput, ...],
    status_preparer_identity_bytes: bytes,
    status_preparer_action_bytes: bytes,
    status_checker_identity_bytes: bytes,
    status_checker_action_bytes: bytes,
) -> CreativeSampleGeneratedReferenceCurrentStatusDecisionV1:
    validated = cast(
        CreativeSampleGeneratedReferenceCurrentStatusDecisionV1,
        _exact_model(
            value, CreativeSampleGeneratedReferenceCurrentStatusDecisionV1, field="decision"
        ),
    )
    rebuilt = build_generated_reference_current_status_decision(
        request=request,
        instruction=instruction,
        chain_inputs=chain_inputs,
        status_preparer_identity_bytes=status_preparer_identity_bytes,
        status_preparer_action_bytes=status_preparer_action_bytes,
        status_checker_identity_bytes=status_checker_identity_bytes,
        status_checker_action_bytes=status_checker_action_bytes,
    )
    if rebuilt != validated:
        _invalid("Decision differs from fresh replay/action rebuild")
    return validated


def verify_generated_reference_current_status_evidence_record(
    value: CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1,
    *,
    chain_inputs: tuple[GeneratedReferenceCurrentStatusExplicitChainInput, ...],
    status_preparer_identity_bytes: bytes,
    status_preparer_action_bytes: bytes,
    status_checker_identity_bytes: bytes,
    status_checker_action_bytes: bytes,
) -> CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1:
    validated = cast(
        CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1,
        _exact_model(
            value, CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1, field="record"
        ),
    )
    rebuilt = build_generated_reference_current_status_evidence_record(
        request=validated.request,
        instruction=validated.instruction,
        decision=validated.decision,
        chain_inputs=chain_inputs,
        status_preparer_identity_bytes=status_preparer_identity_bytes,
        status_preparer_action_bytes=status_preparer_action_bytes,
        status_checker_identity_bytes=status_checker_identity_bytes,
        status_checker_action_bytes=status_checker_action_bytes,
    )
    if rebuilt != validated:
        _invalid("Evidence Record differs from fresh replay/action rebuild")
    return validated


__all__ = [
    "CURRENT_STATUS_CATEGORY_ORDER",
    "CURRENT_STATUS_LIMITATION_CODE_ORDER",
    "CreativeSampleGeneratedReferenceCurrentStatusDecisionV1",
    "CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1",
    "CreativeSampleGeneratedReferenceCurrentStatusInstructionV1",
    "CreativeSampleGeneratedReferenceCurrentStatusRecordAsOfAssessmentReceiptV1",
    "CreativeSampleGeneratedReferenceCurrentStatusRequestV1",
    "CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1",
    "CreativeSampleGeneratedReferenceRightsManifestV1",
    "GENERATED_REFERENCE_CURRENT_STATUS_CHAIN_SCOPE_SHA256_DOMAIN",
    "GENERATED_REFERENCE_CURRENT_STATUS_CHAIN_SHA256_DOMAIN",
    "GENERATED_REFERENCE_CURRENT_STATUS_COVERAGE_SET_SHA256_DOMAIN",
    "GENERATED_REFERENCE_CURRENT_STATUS_DECISION_SHA256_DOMAIN",
    "GENERATED_REFERENCE_CURRENT_STATUS_EVIDENCE_RECORD_SHA256_DOMAIN",
    "GENERATED_REFERENCE_CURRENT_STATUS_EXPLICIT_CHAIN_SET_SHA256_DOMAIN",
    "GENERATED_REFERENCE_CURRENT_STATUS_INSTRUCTION_SHA256_DOMAIN",
    "GENERATED_REFERENCE_CURRENT_STATUS_JOINT_REPLAY_SHA256_DOMAIN",
    "GENERATED_REFERENCE_CURRENT_STATUS_OBSERVATION_SET_SHA256_DOMAIN",
    "GENERATED_REFERENCE_CURRENT_STATUS_POLICY_DOCUMENT_SHA256",
    "GENERATED_REFERENCE_CURRENT_STATUS_POLICY_ID",
    "GENERATED_REFERENCE_CURRENT_STATUS_POLICY_VERSION",
    "GENERATED_REFERENCE_CURRENT_STATUS_RECORD_AS_OF_ASSESSMENT_PROVENANCE_SHA256_DOMAIN",
    "GENERATED_REFERENCE_CURRENT_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_SHA256_DOMAIN",
    "GENERATED_REFERENCE_CURRENT_STATUS_RECORD_AS_OF_ASSESSMENT_SHA256_DOMAIN",
    "GENERATED_REFERENCE_CURRENT_STATUS_REQUEST_SHA256_DOMAIN",
    "GENERATED_REFERENCE_CURRENT_STATUS_SOURCE_OBSERVATION_SHA256_DOMAIN",
    "GENERATED_REFERENCE_CURRENT_STATUS_SUBJECT_CLOSURE_SHA256_DOMAIN",
    "GENERATED_REFERENCE_RIGHTS_MANIFEST_POLICY_DOCUMENT_SHA256",
    "GENERATED_REFERENCE_RIGHTS_MANIFEST_POLICY_ID",
    "GENERATED_REFERENCE_RIGHTS_MANIFEST_POLICY_VERSION",
    "GENERATED_REFERENCE_RIGHTS_MANIFEST_REVIEW_PAYLOAD_SHA256_DOMAIN",
    "GENERATED_REFERENCE_RIGHTS_MANIFEST_SHA256_DOMAIN",
    "GeneratedReferenceAsOfAssessmentError",
    "GeneratedReferenceChainCoverageError",
    "GeneratedReferenceChainReplayError",
    "GeneratedReferenceCurrentStatusAsOfAssessmentResult",
    "GeneratedReferenceCurrentStatusCategoryResultV1",
    "GeneratedReferenceCurrentStatusChainCoverageResult",
    "GeneratedReferenceCurrentStatusChainHeadRefV1",
    "GeneratedReferenceCurrentStatusChainLinkV1",
    "GeneratedReferenceCurrentStatusChainReplayResult",
    "GeneratedReferenceCurrentStatusExplicitChainInput",
    "GeneratedReferenceCurrentStatusJointReplayResult",
    "GeneratedReferenceCurrentStatusObservationRefV1",
    "GeneratedReferenceCurrentStatusObservationInput",
    "GeneratedReferenceCurrentStatusReceiptProcessResult",
    "GeneratedReferenceCurrentStatusSubjectClosureV1",
    "GeneratedReferenceJointReplayError",
    "GeneratedReferenceReceiptError",
    "GeneratedReferenceReviewedRightsScopeV1",
    "GeneratedReferenceRightsCurrentStatusError",
    "GeneratedReferenceRightsManifestEvidenceReferenceV1",
    "GeneratedReferenceRightsManifestEvidenceInput",
    "GeneratedReferenceRightsManifestGateResultV1",
    "GeneratedReferenceRightsScopeProposalV1",
    "MANIFEST_REVIEW_EVIDENCE_CATEGORY_ORDER",
    "MANIFEST_REVIEW_GATE_ORDER",
    "assess_generated_reference_current_status_record_as_of",
    "build_generated_reference_current_status_decision",
    "build_generated_reference_current_status_evidence_record",
    "build_generated_reference_current_status_instruction",
    "build_generated_reference_current_status_record_as_of_assessment_receipt",
    "build_generated_reference_current_status_request",
    "build_generated_reference_current_status_source_observation",
    "build_generated_reference_current_status_subject_closure",
    "build_generated_reference_rights_manifest",
    "cover_generated_reference_current_status_chains",
    "creative_sample_generated_reference_current_status_decision_projection",
    "creative_sample_generated_reference_current_status_decision_sha256",
    "creative_sample_generated_reference_current_status_evidence_record_projection",
    "creative_sample_generated_reference_current_status_evidence_record_sha256",
    "creative_sample_generated_reference_current_status_instruction_projection",
    "creative_sample_generated_reference_current_status_instruction_sha256",
    "creative_sample_generated_reference_current_status_record_as_of_assessment_receipt_projection",
    "creative_sample_generated_reference_current_status_record_as_of_assessment_receipt_sha256",
    "creative_sample_generated_reference_current_status_request_projection",
    "creative_sample_generated_reference_current_status_request_sha256",
    "creative_sample_generated_reference_current_status_source_observation_projection",
    "creative_sample_generated_reference_current_status_source_observation_sha256",
    "creative_sample_generated_reference_rights_manifest_projection",
    "creative_sample_generated_reference_rights_manifest_sha256",
    "generated_reference_contract_document_bytes",
    "generated_reference_current_status_chain_head",
    "generated_reference_current_status_chain_projection",
    "generated_reference_current_status_chain_scope_projection",
    "generated_reference_current_status_chain_scope_sha256",
    "generated_reference_current_status_chain_sha256",
    "generated_reference_current_status_observation_ref",
    "generated_reference_current_status_observation_set_projection",
    "generated_reference_current_status_observation_set_sha256",
    "generated_reference_current_status_explicit_chain_set_projection",
    "generated_reference_current_status_explicit_chain_set_sha256",
    "generated_reference_current_status_coverage_set_projection",
    "generated_reference_current_status_coverage_set_sha256",
    "generated_reference_current_status_joint_replay_projection",
    "generated_reference_current_status_joint_replay_sha256",
    "generated_reference_current_status_record_as_of_assessment_projection",
    "generated_reference_current_status_record_as_of_assessment_sha256",
    "generated_reference_current_status_policy_projection",
    "generated_reference_current_status_subject_closure_projection",
    "generated_reference_current_status_subject_closure_sha256",
    "generated_reference_rights_manifest_policy_projection",
    "generated_reference_rights_manifest_review_payload_projection",
    "generated_reference_rights_manifest_review_payload_sha256",
    "jointly_replay_generated_reference_current_status_record",
    "process_generated_reference_current_status_record_as_of_assessment",
    "replay_generated_reference_current_status_chain",
    "verify_generated_reference_current_status_decision",
    "verify_generated_reference_current_status_evidence_record",
    "verify_generated_reference_current_status_instruction",
    "verify_generated_reference_current_status_record_as_of_assessment_receipt",
    "verify_generated_reference_current_status_request",
    "verify_generated_reference_current_status_source_observation",
    "verify_generated_reference_rights_manifest",
]
