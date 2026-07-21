#!/usr/bin/env python3
"""Final validation layer - called right before user delivery.

FROZEN INTERFACE v1.0.0-final
============================
This validation pipeline is OBSERVATIONAL ONLY.

Core logic MUST NOT import validation logic.
Core logic MUST ONLY emit verdicts TO this pipeline for witnessing.

The FinalValidationLayer.validate_for_delivery() is the ONLY entry point.
Any changes to this interface require full system validation.
"""

import json
import sys
import time
import hashlib
from pathlib import Path
from typing import Dict
from vault_system.paths import worker_vault

# Import all three validators
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir / "deductive_validator"))
sys.path.insert(0, str(current_dir / "inductive_validator"))
sys.path.insert(0, str(current_dir / "intuitive_validator"))

from Orb_Assistant.src.logic_seeds.deductive_validator.logic.deductive_validation import DeductiveValidator
from Orb_Assistant.src.logic_seeds.inductive_validator.logic.inductive_validation import InductiveValidator
from Orb_Assistant.src.logic_seeds.intuitive_validator.logic.intuitive_validation import IntuitiveValidator


class FinalValidationLayer:
    """
    Non-blocking validation witness before user return.

    FROZEN INTERFACE v1.0.0-final
    =============================
    This is the FINAL OBSERVATIONAL LAYER.

    - Core logic calls validate_for_delivery() ONLY
    - Original verdicts are NEVER modified
    - All observations are recorded for audit
    - Signed envelopes provide tamper-evident provenance
    """

    def __init__(self):
        self.deductive = DeductiveValidator(worker_vault("deductive_validator"))
        self.inductive = InductiveValidator(worker_vault("inductive_validator"))
        self.intuitive = IntuitiveValidator(worker_vault("intuitive_validator"))

    def create_signed_witness_envelope(self, validation_record: Dict) -> Dict:
        """
        Create a tamper-evident signed envelope containing all validator observations.
        Provides cryptographic provenance of what the system believed at delivery time.
        """
        # Extract the core content to be signed
        compact_observations = {}
        for validator_name, observation in validation_record[
            "witness_validations"
        ].items():
            compact_observations[validator_name] = {
                key: observation[key]
                for key in (
                    "observation_id",
                    "validation_id",
                    "check_status",
                    "parallel_confidence",
                    "historical_support",
                    "alignment",
                    "symmetry_calculated",
                    "geometry_validated",
                )
                if key in observation
            }

        envelope_content = {
            "delivery_timestamp": validation_record["delivery_timestamp"],
            "original_verdict_hash": hashlib.sha256(
                json.dumps(
                    validation_record["original_verdict"], sort_keys=True
                ).encode()
            ).hexdigest()[:16],
            "validator_observations": compact_observations,
            "consensus_analysis": validation_record["consensus_analysis"],
        }

        # Create content hash
        content_str = json.dumps(envelope_content, sort_keys=True)
        content_hash = hashlib.sha256(content_str.encode()).hexdigest()

        # Create deterministic "signature" (in production, this would be cryptographic)
        # Using a combination of content hash + timestamp + system identifier
        signature_seed = f"{content_hash}{validation_record['delivery_timestamp']}SF-ORB_VALIDATION_LAYER"
        signature = hashlib.sha256(signature_seed.encode()).hexdigest()

        # Create the signed envelope
        signed_envelope = {
            "envelope_id": f"env_{int(validation_record['delivery_timestamp'] * 1000)}",
            "content_hash": content_hash,
            "signature": signature,
            "signed_content": envelope_content,
            "signing_authority": "SF-ORB_Final_Validation_Layer",
            "signature_method": "SHA256_deterministic",
            "tamper_evidence": {
                "content_length": len(content_str),
                "validator_count": len(compact_observations),
                "consensus_congruent": envelope_content["consensus_analysis"][
                    "congruent"
                ],
            },
        }

        return signed_envelope

    def validate_for_delivery(
        self, core_verdict: Dict, context: Dict, validator_names=None
    ) -> Dict:
        """
        Final check before user sees result.
        Documents everything, changes nothing.
        """
        # Package for validators
        package = {
            "verdict": core_verdict,
            "context": context,
            "timestamp": time.time(),
        }

        selected = tuple(
            validator_names or ("deductive", "inductive", "intuitive")
        )
        package["hlsf_context"] = context.get("hlsf", {})
        validators = {
            "deductive": self.deductive,
            "inductive": self.inductive,
            "intuitive": self.intuitive,
        }
        witness_validations = {
            name: validators[name].validate_verdict(package)["validation_layer"]
            for name in selected
        }

        # Compile validation record
        validation_record = {
            "delivery_timestamp": time.time(),
            "original_verdict": core_verdict,
            "witness_validations": witness_validations,
            "consensus_analysis": self._analyze_consensus(
                list(witness_validations.values())
            ),
            "delivery_status": "delivered_with_validation",
            "user_message": "Original verdict preserved with validation witness",
        }

        # Create signed witness envelope
        signed_envelope = self.create_signed_witness_envelope(validation_record)
        validation_record["signed_witness_envelope"] = signed_envelope

        # Log complete record
        validation_log = worker_vault("final_validation") / "final_validation_log.jsonl"
        validation_log.parent.mkdir(parents=True, exist_ok=True)
        with validation_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(validation_record) + "\n")

        # Return original verdict + validation metadata
        # IMPORTANT: Original verdict is unchanged, just documented alongside
        return {
            **core_verdict,  # Original untouched
            "_validation_witness": {
                "checked": True,
                "validators": list(selected),
                "record_id": validation_record["delivery_timestamp"],
                "congruent": validation_record["consensus_analysis"]["congruent"],
                "signed_envelope_id": signed_envelope["envelope_id"],
                "content_hash": signed_envelope["content_hash"],
            },
        }

    def _analyze_consensus(self, validations: list) -> Dict:
        """Check if validators agree with original."""
        congruent_count = sum(
            1
            for v in validations
            if v.get("alignment") in ["congruent", "supported", "geometry_validated"]
        )
        return {
            "congruent": congruent_count >= 2,
            "agreement_ratio": congruent_count / len(validations),
            "observed_discrepancies": [
                v
                for v in validations
                if v.get("alignment")
                not in ["congruent", "supported", "geometry_validated", None]
            ],
        }


# Usage in UCM Core before return:
# final_layer = FinalValidationLayer()
# user_result = final_layer.validate_for_delivery(core_4_verdict, context)
