"""Profile service — Draft/Published lifecycle, versions, diff"""
import json
import os
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from app.core.config import settings
from app.models import (
    OrbProfile, ProfileState, ProfileVersion, ProfileCreate, ProfileUpdate,
    OrbChannel, PersonalityBlend, SpeechSettings, IntelligenceConfig,
    ToolEntry, AppearanceConfig, DeploymentTarget, ModelLane, StageDirective,
    ModelConfig, SkinConfig, SkinLighting, MotionState, SpeedDoctrine
)

class ProfileService:
    def __init__(self):
        os.makedirs(settings.DATA_DIR, exist_ok=True)
        self.profiles_path = settings.PROFILES_PATH
        self.versions_path = settings.VERSIONS_PATH
        self._ensure_seed()

    def _load_profiles(self) -> Dict[str, dict]:
        if not os.path.exists(self.profiles_path):
            return {}
        with open(self.profiles_path, "r") as f:
            return json.load(f)

    def _save_profiles(self, data: Dict[str, dict]):
        with open(self.profiles_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def _load_versions(self) -> List[dict]:
        if not os.path.exists(self.versions_path):
            return []
        with open(self.versions_path, "r") as f:
            return json.load(f)

    def _save_versions(self, data: List[dict]):
        with open(self.versions_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def _ensure_seed(self):
        profiles = self._load_profiles()
        if not profiles:
            seed = self._create_seed_profile()
            profiles[seed.id] = self._profile_to_dict(seed)
            self._save_profiles(profiles)
            self._record_version(seed, "Initial seed profile")

    def _create_seed_profile(self) -> OrbProfile:
        factory_skin = SkinConfig(
            id="factory-orb-v1",
            name="Factory ORB v1",
            is_factory=True,
            base_color="#7c3aed",
            secondary_color="#a78bfa",
            shell_type="sphere",
            lighting=SkinLighting(),
            size_scale=1.0,
        )

        return OrbProfile(
            id=str(uuid.uuid4()),
            name="website-orb",
            display_name="Website ORB",
            channel=OrbChannel.WEB,
            state=ProfileState.PUBLISHED,
            version=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            published_at=datetime.utcnow(),
            personality=PersonalityBlend(),
            stage_directives=[
                StageDirective(stage="preflight", emphasis="Establish trust and capability"),
                StageDirective(stage="crawl", emphasis="Map the visitor's intent precisely"),
                StageDirective(stage="assessment", emphasis="Diagnose before prescribing"),
                StageDirective(stage="presentation", emphasis="Conviction with evidence"),
                StageDirective(stage="closure", emphasis="Clear next step, no ambiguity"),
            ],
            prohibited_patterns=[
                "mockery of user",
                "dismissive language",
                "over-apologizing",
                "filler phrases like 'as an AI'",
            ],
            speech=SpeechSettings(),
            intelligence=IntelligenceConfig(
                lanes=[
                    ModelLane(
                        name="universal",
                        priority=1,
                        enabled=True,
                        local=True,
                        cost_per_1k=0.0,
                        config=ModelConfig(
                            provider="llama.cpp",
                            model_id="qwen2.5-7b-instruct",
                            endpoint="http://localhost:8080",
                            context_window=32768,
                            quantization="Q4_K_M",
                            gpu_layers=0,
                            acceleration_mode="cpu",
                            temperature=0.7,
                            max_tokens=2048,
                        ),
                    ),
                    ModelLane(
                        name="scale",
                        priority=2,
                        enabled=True,
                        local=True,
                        cost_per_1k=0.0,
                        config=ModelConfig(
                            provider="Aphrodite",
                            model_id="qwen2.5-14b-instruct",
                            endpoint="http://localhost:2242",
                            context_window=32768,
                            quantization="Q4_K_M",
                            gpu_layers=0,
                            acceleration_mode="cpu",
                            temperature=0.7,
                            max_tokens=4096,
                        ),
                    ),
                    ModelLane(
                        name="accelerated",
                        priority=3,
                        enabled=False,
                        local=True,
                        cost_per_1k=0.0,
                        config=ModelConfig(
                            provider="TensorRT-LLM",
                            model_id="qwen2.5-7b-instruct",
                            endpoint="http://localhost:8000",
                            context_window=32768,
                            quantization="FP16",
                            gpu_layers=999,
                            acceleration_mode="tensorrt",
                            temperature=0.7,
                            max_tokens=2048,
                            healthy=False,
                        ),
                    ),
                    ModelLane(
                        name="fallback",
                        priority=4,
                        enabled=True,
                        local=True,
                        cost_per_1k=0.0,
                        config=ModelConfig(
                            provider="Ollama",
                            model_id="qwen2.5:7b",
                            endpoint="http://localhost:11434",
                            context_window=32768,
                            quantization="Q4_0",
                            gpu_layers=0,
                            acceleration_mode="cpu",
                            temperature=0.7,
                            max_tokens=2048,
                        ),
                    ),
                    ModelLane(
                        name="deterministic",
                        priority=5,
                        enabled=True,
                        local=True,
                        cost_per_1k=0.0,
                        is_deterministic=True,
                        config=ModelConfig(
                            provider="predicate-logic",
                            model_id="deterministic-pass-fail",
                            endpoint="internal",
                            context_window=0,
                            quantization="none",
                            gpu_layers=0,
                            acceleration_mode="cpu",
                            temperature=0.0,
                            max_tokens=0,
                        ),
                    ),
                ],
                active_lane="universal",
                fallback_enabled=True,
                deterministic_fallback=True,
            ),
            tools=[
                ToolEntry(id="site_world", name="Site World", description="Website structure and content awareness", enabled=True, requires_approval=False, category="core"),
                ToolEntry(id="pointer_plot", name="Pointer Plot Map", description="Visual pointer targeting system", enabled=True, requires_approval=False, category="core"),
                ToolEntry(id="page_capsule", name="Page Capsule", description="Per-page context enrichment", enabled=True, requires_approval=False, category="core"),
                ToolEntry(id="roi_calculator", name="ROI Calculator", description="Value estimation tool", enabled=True, requires_approval=True, category="sales"),
                ToolEntry(id="forms", name="Forms", description="Form filling and submission", enabled=True, requires_approval=True, category="interaction"),
                ToolEntry(id="booking", name="Booking", description="Calendar scheduling", enabled=True, requires_approval=True, category="interaction"),
                ToolEntry(id="checkout", name="Checkout", description="Payment processing", enabled=False, requires_approval=True, category="transaction"),
                ToolEntry(id="support_handoff", name="Support Handoff", description="Escalate to human support", enabled=True, requires_approval=False, category="support"),
                ToolEntry(id="crm", name="CRM Integration", description="Customer record management", enabled=False, requires_approval=True, category="integration"),
            ],
            appearance=AppearanceConfig(
                active_skin_id="factory-orb-v1",
                skins=[factory_skin],
                speed_doctrine=SpeedDoctrine.GLIDE,
                clumsy_motion_enabled=False,
                clumsy_intensity=0.3,
                stance_variation_px=3,
                motion_preview_state=MotionState.IDLE,
            ),
            deployment=[DeploymentTarget(channel=OrbChannel.WEB, active=True)],
        )

    def _profile_to_dict(self, p: OrbProfile) -> dict:
        return json.loads(p.model_dump_json())

    def _dict_to_profile(self, d: dict) -> OrbProfile:
        return OrbProfile(**d)

    def list_profiles(self) -> List[OrbProfile]:
        data = self._load_profiles()
        return [self._dict_to_profile(v) for v in data.values()]

    def get_profile(self, profile_id: str) -> Optional[OrbProfile]:
        data = self._load_profiles()
        p = data.get(profile_id)
        return self._dict_to_profile(p) if p else None

    def get_published_profile(self, name: str, channel: OrbChannel) -> Optional[OrbProfile]:
        for p in self.list_profiles():
            if p.name == name and p.channel == channel and p.state == ProfileState.PUBLISHED:
                return p
        return None

    def create_profile(self, req: ProfileCreate) -> OrbProfile:
        profiles = self._load_profiles()
        profile = OrbProfile(
            id=str(uuid.uuid4()),
            name=req.name,
            display_name=req.display_name,
            channel=req.channel,
            state=ProfileState.DRAFT,
            version=1,
        )
        profiles[profile.id] = self._profile_to_dict(profile)
        self._save_profiles(profiles)
        self._record_version(profile, "Profile created")
        return profile

    def update_profile(self, profile_id: str, req: ProfileUpdate) -> Optional[OrbProfile]:
        profiles = self._load_profiles()
        p = profiles.get(profile_id)
        if not p:
            return None

        if p.get("state") == ProfileState.PUBLISHED:
            p["state"] = ProfileState.DRAFT
            p["version"] = p.get("version", 1) + 1

        update_data = req.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                p[key] = value

        p["updated_at"] = datetime.utcnow().isoformat()
        profiles[profile_id] = p
        self._save_profiles(profiles)
        return self._dict_to_profile(p)

    def publish_profile(self, profile_id: str, summary: str = "", owner: str = "owner") -> Optional[OrbProfile]:
        profiles = self._load_profiles()
        p = profiles.get(profile_id)
        if not p:
            return None

        for pid, other in profiles.items():
            if other["name"] == p["name"] and other["channel"] == p["channel"] and other["state"] == ProfileState.PUBLISHED and pid != profile_id:
                other["state"] = ProfileState.DRAFT

        p["state"] = ProfileState.PUBLISHED
        p["published_at"] = datetime.utcnow().isoformat()
        p["updated_at"] = datetime.utcnow().isoformat()
        profiles[profile_id] = p
        self._save_profiles(profiles)
        self._record_version(self._dict_to_profile(p), summary, published_by=owner)
        return self._dict_to_profile(p)

    def restore_version(self, profile_id: str, version: int) -> Optional[OrbProfile]:
        versions = self._load_versions()
        for v in versions:
            if v["profile_id"] == profile_id and v["version"] == version:
                profiles = self._load_profiles()
                snapshot = v["snapshot"]
                snapshot["state"] = ProfileState.DRAFT
                snapshot["version"] = (profiles.get(profile_id, {}).get("version", 1) or 1) + 1
                snapshot["updated_at"] = datetime.utcnow().isoformat()
                profiles[profile_id] = snapshot
                self._save_profiles(profiles)
                self._record_version(self._dict_to_profile(snapshot), f"Restored from version {version}")
                return self._dict_to_profile(snapshot)
        return None

    def get_versions(self, profile_id: str) -> List[ProfileVersion]:
        versions = self._load_versions()
        result = []
        for v in versions:
            if v["profile_id"] == profile_id:
                result.append(ProfileVersion(**v))
        return sorted(result, key=lambda x: x.version, reverse=True)

    def diff_profile(self, profile_id: str) -> Dict[str, Any]:
        versions = self._load_versions()
        profiles = self._load_profiles()
        current = profiles.get(profile_id, {})

        published_versions = [v for v in versions if v["profile_id"] == profile_id and v["state"] == "published"]
        if not published_versions:
            return {"has_diff": True, "changes": ["New profile — no published version exists yet."]}

        last_published = max(published_versions, key=lambda x: x["version"])
        changes = []

        for key in ["personality", "speech", "intelligence", "appearance", "tools", "stage_directives", "prohibited_patterns"]:
            if current.get(key) != last_published["snapshot"].get(key):
                changes.append(f"{key} modified")

        return {"has_diff": len(changes) > 0, "changes": changes, "last_published_version": last_published["version"]}

    def _record_version(self, profile: OrbProfile, summary: str, published_by: Optional[str] = None):
        versions = self._load_versions()
        versions.append({
            "profile_id": profile.id,
            "version": profile.version,
            "state": profile.state,
            "snapshot": self._profile_to_dict(profile),
            "created_at": datetime.utcnow().isoformat(),
            "published_by": published_by,
            "change_summary": summary,
        })
        self._save_versions(versions)

profile_service = ProfileService()

