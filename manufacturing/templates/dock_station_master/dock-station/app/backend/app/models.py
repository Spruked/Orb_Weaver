"""Pydantic models for ORB Dock Station v2.1"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum

class ProfileState(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"

class OrbChannel(str, Enum):
    WEB = "web"
    TELEPHONE = "telephone"
    SIP = "sip"

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

class PointerStatus(str, Enum):
    NEW = "new"
    VERIFIED = "verified"
    RECOVERED = "recovered"
    OWNER_VERIFIED = "owner_verified"
    DEPRECATED = "deprecated"
    REMOVED = "removed"

class SpeedDoctrine(str, Enum):
    GLIDE = "glide"
    BRISK = "brisk"
    URGENT = "urgent"

class MotionState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    POINTER = "pointer"
    SUCCESS = "success"
    WARNING = "warning"
    FAILURE = "failure"

class PersonalityBlend(BaseModel):
    conviction: float = Field(0.75, ge=0.0, le=1.0)
    warmth: float = Field(0.60, ge=0.0, le=1.0)
    humor: float = Field(0.30, ge=0.0, le=1.0)
    directness: float = Field(0.80, ge=0.0, le=1.0)
    humor_requires_evidence: bool = True
    first_person_mandatory: bool = True
    anti_decoration_rule: bool = True

class StageDirective(BaseModel):
    stage: str
    emphasis: str
    tone_note: str = ""

class SpeechSettings(BaseModel):
    allow_interruption: bool = True
    interruption_sensitivity: float = Field(0.5, ge=0.0, le=1.0)
    pause_timeout_ms: int = Field(800, ge=100, le=5000)
    prefix_padding_ms: int = Field(300, ge=0, le=1000)
    microphone_sensitivity: float = Field(0.7, ge=0.0, le=1.0)
    reengage_after_silence: bool = True
    reengage_delay_ms: int = Field(15000, ge=1000, le=60000)
    greeting_text: str = "Hello. I'm Weaver. How can I help you today?"
    tone_check_enabled: bool = True

class ModelConfig(BaseModel):
    provider: str = "llama.cpp"
    model_id: str = "qwen2.5-7b-instruct"
    model_file: Optional[str] = None
    endpoint: str = "http://localhost:8080"
    context_window: int = 32768
    quantization: str = "Q4_K_M"
    gpu_layers: int = 0
    acceleration_mode: str = "cpu"
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: int = 2048
    top_p: float = Field(0.9, ge=0.0, le=1.0)
    top_k: int = 40
    repeat_penalty: float = 1.1
    healthy: bool = True
    last_latency_ms: Optional[int] = None
    last_tested: Optional[datetime] = None

class ModelLane(BaseModel):
    name: str
    priority: int = 1
    enabled: bool = True
    local: bool = True
    cost_per_1k: float = 0.0
    config: ModelConfig = Field(default_factory=ModelConfig)
    is_deterministic: bool = False

class IntelligenceConfig(BaseModel):
    lanes: List[ModelLane] = []
    active_lane: str = "universal"
    fallback_enabled: bool = True
    deterministic_fallback: bool = True

class ToolEntry(BaseModel):
    id: str
    name: str
    description: str
    enabled: bool = False
    requires_approval: bool = True
    category: str = "general"

class SkinLighting(BaseModel):
    ambient: str = "#1a1a2e"
    glow_color: str = "#7c3aed"
    glow_intensity: float = Field(0.6, ge=0.0, le=1.0)
    rim_light: str = "#a78bfa"
    rim_intensity: float = Field(0.3, ge=0.0, le=1.0)

class SkinDecal(BaseModel):
    id: str
    label: str
    url: Optional[str] = None
    position: str = "center"
    scale: float = Field(1.0, ge=0.1, le=3.0)
    opacity: float = Field(0.8, ge=0.0, le=1.0)

class SkinConfig(BaseModel):
    id: str = "factory-orb-v1"
    name: str = "Factory ORB v1"
    is_factory: bool = True
    base_color: str = "#7c3aed"
    secondary_color: str = "#a78bfa"
    shell_type: str = "sphere"
    texture_url: Optional[str] = None
    texture_scale: float = Field(1.0, ge=0.1, le=5.0)
    lighting: SkinLighting = Field(default_factory=SkinLighting)
    size_scale: float = Field(1.0, ge=0.5, le=3.0)
    decals: List[SkinDecal] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AppearanceConfig(BaseModel):
    active_skin_id: str = "factory-orb-v1"
    skins: List[SkinConfig] = []
    speed_doctrine: SpeedDoctrine = SpeedDoctrine.GLIDE
    clumsy_motion_enabled: bool = False
    clumsy_intensity: float = Field(0.3, ge=0.0, le=1.0)
    stance_variation_px: int = 3
    motion_preview_state: MotionState = MotionState.IDLE

class DeploymentTarget(BaseModel):
    channel: OrbChannel
    published_profile_id: Optional[str] = None
    active: bool = True

class LiveTestSession(BaseModel):
    session_id: str
    profile_id: str
    url: str = "http://localhost:3000"
    route: str = "/"
    status: Literal["idle", "listening", "thinking", "speaking", "error"] = "idle"
    started_at: datetime = Field(default_factory=datetime.utcnow)
    microphone_allowed: bool = False
    speaker_active: bool = False
    muted: bool = False
    mobile_simulation: bool = False
    current_stage: str = "preflight"
    detected_intent: Optional[str] = None
    confidence: float = 0.0
    latency_ms: int = 0
    active_lane: str = ""
    pointer_target: Optional[Dict[str, Any]] = None
    transcript: List[Dict[str, Any]] = []
    allowed_actions: List[str] = []
    tool_calls: List[Dict[str, Any]] = []
    events: List[Dict[str, Any]] = []

class LiveTestControl(BaseModel):
    action: Literal["start", "stop", "mute", "unmute", "reset", "reload_site_world", "set_route"]
    route: Optional[str] = None
    url: Optional[str] = None

class OrbProfile(BaseModel):
    id: str
    name: str
    display_name: str
    channel: OrbChannel = OrbChannel.WEB
    state: ProfileState = ProfileState.DRAFT
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    published_at: Optional[datetime] = None
    personality: PersonalityBlend = Field(default_factory=PersonalityBlend)
    stage_directives: List[StageDirective] = []
    prohibited_patterns: List[str] = []
    speech: SpeechSettings = Field(default_factory=SpeechSettings)
    intelligence: IntelligenceConfig = Field(default_factory=IntelligenceConfig)
    tools: List[ToolEntry] = []
    appearance: AppearanceConfig = Field(default_factory=AppearanceConfig)
    deployment: List[DeploymentTarget] = []

class ProfileVersion(BaseModel):
    profile_id: str
    version: int
    state: ProfileState
    snapshot: Dict[str, Any]
    created_at: datetime
    published_by: Optional[str] = None
    change_summary: str = ""

class ProfileCreate(BaseModel):
    name: str
    display_name: str
    channel: OrbChannel = OrbChannel.WEB

class ProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    personality: Optional[PersonalityBlend] = None
    speech: Optional[SpeechSettings] = None
    intelligence: Optional[IntelligenceConfig] = None
    tools: Optional[List[ToolEntry]] = None
    appearance: Optional[AppearanceConfig] = None
    stage_directives: Optional[List[StageDirective]] = None
    prohibited_patterns: Optional[List[str]] = None

class PublishRequest(BaseModel):
    change_summary: str = ""

class HealthReport(BaseModel):
    pointer_confidence: float = Field(0.0, ge=0.0, le=1.0)
    model_reachability: HealthStatus
    voice_reachability: HealthStatus
    overall: HealthStatus
    checks: Dict[str, Any] = {}

class ConversationSession(BaseModel):
    session_id: str
    profile_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    transcript: List[Dict[str, Any]] = []
    outcome: Optional[str] = None
    stage_transitions: List[str] = []
    actions_requested: int = 0
    actions_approved: int = 0
    actions_verified: int = 0

class StatisticsSnapshot(BaseModel):
    profile_id: str
    period_start: datetime
    period_end: datetime
    conversations_total: int = 0
    avg_time_to_first_word_ms: Optional[float] = None
    avg_speech_recognition_ms: Optional[float] = None
    avg_llm_response_ms: Optional[float] = None
    avg_tts_generation_ms: Optional[float] = None
    cache_hit_percent: float = 0.0
    interrupted_responses: int = 0
    failed_mic_permissions: int = 0
    pointer_success_rate: float = 0.0
    guided_journeys_completed: int = 0
    actions_requested: int = 0
    actions_approved: int = 0
    actions_verified: int = 0
    visitor_abandonment_stage: Optional[str] = None
    local_vs_api_cost_ratio: float = 1.0

class DiagnosticEntry(BaseModel):
    id: str
    category: str
    severity: Literal["info", "warning", "critical"]
    message: str
    remediation: Optional[str] = None
    detected_at: datetime
    resolved_at: Optional[datetime] = None
    auto_resolvable: bool = False

class TryItLiveResult(BaseModel):
    test_type: str
    passed: bool
    notes: str = ""
    audio_url: Optional[str] = None
    latency_ms: Optional[int] = None
    tone_flags: List[str] = []

class OwnerLogin(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    owner: Dict[str, Any]

class SkinUploadResponse(BaseModel):
    skin_id: str
    name: str
    message: str

class ModelTestResult(BaseModel):
    lane_name: str
    passed: bool
    latency_ms: int
    ttf_ms: int
    sample_output: str
    error: Optional[str] = None
