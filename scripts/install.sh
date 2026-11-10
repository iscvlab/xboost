#!/usr/bin/env bash
# XBoost Composable Agent Skills (v3.5.0) - Universal Installer (macOS & Linux) - iscvlab/xboost
# Links the 15-skill XBoost (/x*) suite into Claude Code (~/.claude/skills), Grok (~/.grok/skills),
# Gemini/Antigravity (~/.gemini/config/skills), and Cursor/Codex (~/.agents/skills).

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_SRC="$SCRIPT_DIR/skills"

LEGACY_DIRS=(
    "xpublish-audit" "xpublish-qgis"
    "boostx" "briefx" "contextx" "create-skillx" "deep-researchx"
    "kickoffx" "layax" "learnx" "mousex" "obsidianx" "ocrx" "planx" "publishx-audit"
    "publishx-qgis" "researchx" "syncx" "ultrax" "unlimited-ocr"
    "brief" "context" "create-skill" "deep-research" "kickoff" "laya"
    "obsidian-vault" "ocr" "publish-audit" "publish-qgis" "research" "update-doc"
)

echo "============================================================"
echo "  ⚡ XBoost Agent Skills (v3.5.0) - Universal Installer"
echo "============================================================"
echo "Source: $SKILLS_SRC"

MODE="copy"
TARGET_DIR="${AGENT_SKILLS_DIR:-}"
WORKSPACE_DIR=""
FLAG=""

while [ $# -gt 0 ]; do
    case "$1" in
        --symlink)
            MODE="symlink"
            shift
            ;;
        --target)
            TARGET_DIR="$2"
            shift 2
            ;;
        --target=*)
            TARGET_DIR="${1#*=}"
            shift
            ;;
        --all|--claude|--antigravity|--grok|--agents|--codex)
            FLAG="$1"
            shift
            ;;
        *)
            if [ -z "$WORKSPACE_DIR" ] && [ -d "$1" ]; then
                WORKSPACE_DIR="$1"
            fi
            shift
            ;;
    esac
done

install_to() {
    local target_dir="$1"
    local name="$2"

    mkdir -p "$target_dir"
    echo ""
    echo "Installing into $name ($target_dir)..."

    for old_name in "${LEGACY_DIRS[@]}"; do
        local old_dest="$target_dir/$old_name"
        if [ -L "$old_dest" ] || [ -d "$old_dest" ]; then
            rm -rf "$old_dest"
            echo "  - Removed legacy /$old_name"
        fi
    done

    for skill in "$SKILLS_SRC"/*; do
        if [ -d "$skill" ]; then
            local skill_name
            skill_name="$(basename "$skill")"
            local dest="$target_dir/$skill_name"

            if [ -L "$dest" ] || [ -d "$dest" ]; then
                rm -rf "$dest"
            fi
            if [ "$MODE" == "symlink" ]; then
                ln -s "$skill" "$dest"
                echo "  ✓ Linked /$skill_name"
            else
                cp -R "$skill" "$dest"
                echo "  ✓ Installed /$skill_name"
            fi
        fi
    done
}

NO_FLAG=false
if [ -z "$FLAG" ] && [ -z "$TARGET_DIR" ] && [ -z "$WORKSPACE_DIR" ]; then
    NO_FLAG=true
fi

# 0. Custom Agent Target (--target <dir> or $AGENT_SKILLS_DIR)
if [ -n "$TARGET_DIR" ]; then
    install_to "$TARGET_DIR" "Custom Agent Target ($TARGET_DIR)"
fi

# 1. Claude Code
if [ "$FLAG" == "--claude" ] || [ "$FLAG" == "--all" ] || { [ "$NO_FLAG" == true ] && [ -d "$HOME/.claude" ]; }; then
    install_to "$HOME/.claude/skills" "Claude Code"
fi

# 2. Gemini / Antigravity
if [ "$FLAG" == "--antigravity" ] || [ "$FLAG" == "--all" ] || { [ "$NO_FLAG" == true ] && [ -d "$HOME/.gemini" ]; }; then
    install_to "$HOME/.gemini/config/skills" "Gemini / Antigravity"
fi

# 3. Grok
GROK_ROOT="${GROK_HOME:-$HOME/.grok}"
if [ "$FLAG" == "--grok" ] || [ "$FLAG" == "--all" ] || { [ "$NO_FLAG" == true ] && [ -d "$GROK_ROOT" ]; }; then
    install_to "$GROK_ROOT/skills" "Grok"
fi

# 4. Universal ~/.agents/skills & ~/.codex/skills (Cursor, Codex, Windsurf, Cline, Continue, OpenHands, Local LLM Agents)
if [ "$FLAG" == "--agents" ] || [ "$FLAG" == "--all" ] || { [ "$NO_FLAG" == true ] && [ -d "$HOME/.agents" ]; }; then
    install_to "$HOME/.agents/skills" "Universal .agents (Cursor / Codex / Windsurf / Local LLM Agents)"
fi
if [ "$FLAG" == "--codex" ] || [ "$FLAG" == "--all" ] || { [ "$NO_FLAG" == true ] && [ -d "$HOME/.codex" ]; }; then
    install_to "$HOME/.codex/skills" "Codex (.codex)"
fi

# 5. Target workspace if provided
if [ -n "$WORKSPACE_DIR" ] && [ -d "$WORKSPACE_DIR" ]; then
    install_to "$WORKSPACE_DIR/.agents/skills" "Workspace .agents ($WORKSPACE_DIR)"
    if [ -d "$WORKSPACE_DIR/.claude" ] || [ "$FLAG" == "--claude" ] || [ "$FLAG" == "--all" ]; then
        install_to "$WORKSPACE_DIR/.claude/skills" "Workspace .claude ($WORKSPACE_DIR)"
    fi
    if [ -d "$WORKSPACE_DIR/.grok" ] || [ "$FLAG" == "--grok" ]; then
        install_to "$WORKSPACE_DIR/.grok/skills" "Workspace .grok ($WORKSPACE_DIR)"
    fi
fi

echo ""
echo "============================================================"
echo "  ✓ XBoost v3.5.0 Installation Complete! All 15 /x* skills ready."
echo "============================================================"
