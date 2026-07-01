// ORB SKIN LOADER — TAURI (Rust core)
// File: src-tauri/src/skin_loader.rs
//
// Cargo.toml additions needed:
//   [dependencies]
//   zip = "0.6"
//   sha2 = "0.10"
//   serde = { version = "1", features = ["derive"] }
//   serde_json = "1"
//   tauri = { version = "2", features = ["protocol-asset"] }
//   hex = "0.4"
//
// Registers a Tauri command: load_orb_skin(path: String) -> Result<SkinBundle, String>
// Assets served via asset:// custom protocol or local file path

use std::collections::HashMap;
use std::fs;
use std::io::Read;
use std::path::{Path, PathBuf};
use std::sync::Mutex;

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use tauri::{AppHandle, Emitter, Manager, State};
use zip::ZipArchive;

// ─────────────────────────────────────────────
// STATE  (stored in Tauri managed state)
// ─────────────────────────────────────────────

pub struct SkinState {
    pub active: Option<SkinBundle>,
    pub rollback: Option<SkinBundle>,
    pub active_path: Option<PathBuf>,
    pub rollback_path: Option<PathBuf>,
}

impl Default for SkinState {
    fn default() -> Self {
        Self {
            active: None,
            rollback: None,
            active_path: None,
            rollback_path: None,
        }
    }
}

pub type ManagedSkinState = Mutex<SkinState>;

// ─────────────────────────────────────────────
// MANIFEST TYPES  (mirrors TS types)
// ─────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrbSkinManifest {
    pub schema_version: String,
    pub skin_id: String,
    pub name: String,
    pub version: String,
    pub description: Option<String>,
    pub creator: ManifestCreator,
    pub classification: ManifestClassification,
    pub visuals: ManifestVisuals,
    pub behavior_limits: ManifestBehaviorLimits,
    pub rights: ManifestRights,
    pub integrity: ManifestIntegrity,
    // Optional sections
    pub marketplace: Option<serde_json::Value>,
    pub collectible: Option<serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ManifestCreator {
    pub creator_id: String,
    pub display_name: String,
    pub verified: Option<bool>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ManifestClassification {
    pub tier: String,
    pub edition_type: String,
    pub supported_orbs: Vec<String>,
    pub commercial_use: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ManifestVisuals {
    pub preview: String,
    pub body_asset: String,
    pub docked_icon: String,
    pub animations: Vec<String>,
    pub particle_profile: Option<String>,
    pub sounds: Option<Vec<String>>,
    pub theme_tokens: Option<HashMap<String, String>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ManifestBehaviorLimits {
    pub changes_visuals_only: bool,
    pub may_change_voice_style: bool,
    pub may_change_personality_language: bool,
    pub may_add_permissions: bool,
    pub may_add_tools: bool,
    pub may_add_network_access: bool,
    pub may_add_llm_access: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ManifestRights {
    pub license_type: String,
    pub transferable: bool,
    pub resellable: bool,
    pub max_active_orbs: u32,
    pub expiry_date: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ManifestIntegrity {
    pub package_hash: String,
    pub manifest_hash: String,
    pub publisher_signature: String,
    pub signed_at: String,
    pub runtime_min_version: String,
    pub runtime_max_version: Option<String>,
}

// ─────────────────────────────────────────────
// BUNDLE  (what we emit to the webview)
// ─────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SkinBundle {
    pub skin_id: String,
    pub name: String,
    pub manifest: OrbSkinManifest,
    pub urls: SkinUrls,
    pub theme_tokens: HashMap<String, String>,
    pub loaded_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SkinUrls {
    pub preview: String,
    pub body_asset: String,
    pub docked_icon: String,
    pub animations: HashMap<String, String>,
    pub particle_profile: Option<String>,
    pub sounds: HashMap<String, String>,
}

// ─────────────────────────────────────────────
// VALIDATION
// ─────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize)]
pub struct ValidationResult {
    pub valid: bool,
    pub skin_id: String,
    pub errors: Vec<ValidationIssue>,
    pub warnings: Vec<ValidationIssue>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ValidationIssue {
    pub code: String,
    pub field: Option<String>,
    pub message: String,
}

fn validate_manifest(
    manifest: &OrbSkinManifest,
    for_target: &str,
    package_hash: &str,
) -> ValidationResult {
    let mut errors: Vec<ValidationIssue> = Vec::new();
    let warnings: Vec<ValidationIssue> = Vec::new();

    // Schema version
    if manifest.schema_version != "1.0" {
        errors.push(ValidationIssue {
            code: "SCHEMA_VERSION_MISMATCH".into(),
            field: Some("schema_version".into()),
            message: format!("Expected 1.0, got {}", manifest.schema_version),
        });
    }

    // Target compatibility
    let supported = &manifest.classification.supported_orbs;
    if !supported.contains(&for_target.to_string()) && !supported.contains(&"all".to_string()) {
        errors.push(ValidationIssue {
            code: "UNSUPPORTED_TARGET".into(),
            field: Some("classification.supported_orbs".into()),
            message: format!(
                "Skin does not support target \"{}\". Supported: {}",
                for_target,
                supported.join(", ")
            ),
        });
    }

    // Behavior hard walls — these are non-negotiable
    let bl = &manifest.behavior_limits;
    if !bl.changes_visuals_only {
        errors.push(ValidationIssue {
            code: "BEHAVIOR_VIOLATION".into(),
            field: Some("behavior_limits.changes_visuals_only".into()),
            message: "changes_visuals_only must be true".into(),
        });
    }
    for (field, value) in [
        ("may_add_permissions", bl.may_add_permissions),
        ("may_add_tools", bl.may_add_tools),
        ("may_add_network_access", bl.may_add_network_access),
        ("may_add_llm_access", bl.may_add_llm_access),
    ] {
        if value {
            errors.push(ValidationIssue {
                code: "BEHAVIOR_VIOLATION".into(),
                field: Some(format!("behavior_limits.{}", field)),
                message: format!("{} must be false", field),
            });
        }
    }

    // Hash check
    let stored_hash = manifest.integrity.package_hash
        .trim_start_matches("sha256:")
        .to_lowercase();
    let actual_hash = package_hash
        .trim_start_matches("sha256:")
        .to_lowercase();
    if stored_hash != actual_hash {
        errors.push(ValidationIssue {
            code: "HASH_MISMATCH".into(),
            field: Some("integrity.package_hash".into()),
            message: format!(
                "Hash mismatch. Stored: {}... Actual: {}...",
                &stored_hash[..12.min(stored_hash.len())],
                &actual_hash[..12.min(actual_hash.len())]
            ),
        });
    }

    ValidationResult {
        valid: errors.is_empty(),
        skin_id: manifest.skin_id.clone(),
        errors,
        warnings,
    }
}

// ─────────────────────────────────────────────
// TAURI COMMANDS
// ─────────────────────────────────────────────

/// Load a .orbskin file. Call from JS: invoke("load_orb_skin", { path: "..." })
#[tauri::command]
pub async fn load_orb_skin(
    app: AppHandle,
    state: State<'_, ManagedSkinState>,
    path: String,
) -> Result<SkinBundle, String> {
    let skin_path = PathBuf::from(&path);

    // Read bytes
    let raw = fs::read(&skin_path).map_err(|e| format!("Cannot read file: {e}"))?;

    // Compute hash
    let mut hasher = Sha256::new();
    hasher.update(&raw);
    let hash_hex = hex::encode(hasher.finalize());
    let package_hash = format!("sha256:{hash_hex}");

    // Unzip
    let cursor = std::io::Cursor::new(raw);
    let mut archive = ZipArchive::new(cursor).map_err(|e| format!("Invalid zip: {e}"))?;

    // Read manifest
    let manifest_text = {
        let mut mf = archive
            .by_name("manifest.json")
            .map_err(|_| "manifest.json not found in package")?;
        let mut buf = String::new();
        mf.read_to_string(&mut buf).map_err(|e| format!("Cannot read manifest: {e}"))?;
        buf
    };
    let manifest: OrbSkinManifest =
        serde_json::from_str(&manifest_text).map_err(|e| format!("Invalid manifest JSON: {e}"))?;

    // Validate
    let validation = validate_manifest(&manifest, "desktop", &package_hash);
    if !validation.valid {
        let error_msgs: Vec<String> = validation.errors.iter().map(|e| e.message.clone()).collect();
        return Err(format!("Skin validation failed: {}", error_msgs.join("; ")));
    }

    // Extract to app data dir
    let app_data = app
        .path()
        .app_data_dir()
        .map_err(|e| format!("Cannot get app data dir: {e}"))?;
    let skin_dir = app_data.join("skins").join(&manifest.skin_id);
    fs::create_dir_all(&skin_dir).map_err(|e| format!("Cannot create skin dir: {e}"))?;

    // Write all files except manifest
    for i in 0..archive.len() {
        let mut file = archive.by_index(i).map_err(|e| format!("Zip error: {e}"))?;
        let name = file.name().to_string();
        if name == "manifest.json" || file.is_dir() {
            continue;
        }
        let dest = skin_dir.join(&name);
        if let Some(parent) = dest.parent() {
            fs::create_dir_all(parent).ok();
        }
        let mut bytes = Vec::new();
        file.read_to_end(&mut bytes).map_err(|e| format!("Read error: {e}"))?;
        fs::write(&dest, bytes).map_err(|e| format!("Write error: {e}"))?;
    }

    // Build URL helper — use convertFileSrc on the JS side, or return absolute paths
    // Tauri v2: frontend uses convertFileSrc() to turn paths into asset:// URLs
    let to_path = |filename: &str| -> String {
        skin_dir.join(filename).to_string_lossy().to_string()
    };

    let mut animations: HashMap<String, String> = HashMap::new();
    for anim in &manifest.visuals.animations {
        animations.insert(anim.clone(), to_path(&format!("animations/{anim}")));
    }

    let mut sounds: HashMap<String, String> = HashMap::new();
    for snd in manifest.visuals.sounds.iter().flatten() {
        sounds.insert(snd.clone(), to_path(&format!("sounds/{snd}")));
    }

    let bundle = SkinBundle {
        skin_id: manifest.skin_id.clone(),
        name: manifest.name.clone(),
        urls: SkinUrls {
            preview: to_path(&manifest.visuals.preview),
            body_asset: to_path(&manifest.visuals.body_asset),
            docked_icon: to_path(&manifest.visuals.docked_icon),
            animations,
            particle_profile: manifest
                .visuals
                .particle_profile
                .as_ref()
                .map(|p| to_path(p)),
            sounds,
        },
        theme_tokens: manifest.visuals.theme_tokens.clone().unwrap_or_default(),
        manifest,
        loaded_at: chrono::Utc::now().to_rfc3339(),
    };

    // Store rollback
    {
        let mut s = state.lock().unwrap();
        s.rollback = s.active.clone();
        s.rollback_path = s.active_path.clone();
        s.active = Some(bundle.clone());
        s.active_path = Some(skin_path);
    }

    // Emit to webview
    app.emit("skin:applied", &bundle).ok();

    Ok(bundle)
}

/// Rollback to the previous skin
#[tauri::command]
pub async fn rollback_orb_skin(
    app: AppHandle,
    state: State<'_, ManagedSkinState>,
) -> Result<SkinBundle, String> {
    let mut s = state.lock().unwrap();
    let prev = s.rollback.clone().ok_or("No rollback skin available")?;
    let current = s.active.clone();
    s.active = Some(prev.clone());
    s.rollback = current;
    app.emit("skin:applied", &prev).ok();
    Ok(prev)
}

/// Get active skin info
#[tauri::command]
pub fn get_active_skin(
    state: State<'_, ManagedSkinState>,
) -> Option<HashMap<String, String>> {
    let s = state.lock().unwrap();
    s.active.as_ref().map(|b| {
        let mut m = HashMap::new();
        m.insert("skin_id".into(), b.skin_id.clone());
        m.insert("name".into(), b.name.clone());
        m
    })
}

/// Clear active skin
#[tauri::command]
pub async fn clear_orb_skin(
    app: AppHandle,
    state: State<'_, ManagedSkinState>,
) -> Result<(), String> {
    let mut s = state.lock().unwrap();
    s.rollback = s.active.clone();
    s.active = None;
    app.emit("skin:cleared", ()).ok();
    Ok(())
}

// ─────────────────────────────────────────────
// REGISTER  — call in main.rs
// ─────────────────────────────────────────────

// In your src-tauri/src/main.rs or lib.rs builder:
//
// use crate::skin_loader::{
//     ManagedSkinState, SkinState,
//     load_orb_skin, rollback_orb_skin, get_active_skin, clear_orb_skin
// };
//
// tauri::Builder::default()
//     .manage(ManagedSkinState::new(SkinState::default()))
//     .invoke_handler(tauri::generate_handler![
//         load_orb_skin,
//         rollback_orb_skin,
//         get_active_skin,
//         clear_orb_skin,
//     ])
//     .run(tauri::generate_context!())
//     .expect("error running tauri app");
