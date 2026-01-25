import argparse
import subprocess
import sys
from pathlib import Path
import os

# ============================================================
# Paths (adjusted to YOUR repo structure)
# ============================================================

ROOT = Path(__file__).resolve().parent

CSV_SCRIPTS = ROOT / "inputs" / "scripts"     # build_config_from_csv.py lives here
SIM_SCRIPTS = ROOT / "scripts"                # run_simulation.py lives here
CONFIG_DIR = ROOT / "inputs" / "config" 
OUTPUTS_DIR = ROOT / "outputs"


# ============================================================
# CLI
# ============================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="DDP master orchestration: CSV → JSON → Simulation"
    )

    parser.add_argument(
        "--inputs",
        type=str,
        required=True,
        help="Path to input CSV directory (e.g. inputs/)",
    )

    parser.add_argument(
        "--outdir",
        type=str,
        default=str(OUTPUTS_DIR),
        help="Directory to write simulation outputs",
    )

    return parser.parse_args()


# ============================================================
# Main orchestration
# ============================================================

def main():
    args = parse_args()

    inputs_dir = Path(args.inputs).resolve()
    outdir = Path(args.outdir).resolve()

    if not inputs_dir.exists():
        print(f"[ERROR] Inputs directory not found: {inputs_dir}")
        sys.exit(1)

    if not (CSV_SCRIPTS / "build_config_from_csv.py").exists():
        print("[ERROR] build_config_from_csv.py not found at:")
        print(CSV_SCRIPTS / "build_config_from_csv.py")
        sys.exit(1)

    if not (SIM_SCRIPTS / "run_simulation.py").exists():
        print("[ERROR] run_simulation.py not found at:")
        print(SIM_SCRIPTS / "run_simulation.py")
        sys.exit(1)

    CONFIG_DIR.mkdir(exist_ok=True)
    outdir.mkdir(parents=True, exist_ok=True)

    generated_config = CONFIG_DIR / "generated_from_csv.json"

    # ============================================================
    # STEP 1: Build JSON config from CSVs
    # ============================================================

    print("=" * 70)
    print("[STEP 1] Building JSON config from CSV inputs")
    print("=" * 70)

    build_cmd = [
        sys.executable,
        str(CSV_SCRIPTS / "build_config_from_csv.py"),
    ]

    try:
        subprocess.run(
            build_cmd,
            cwd=str(ROOT),
            check=True,
        )
    except subprocess.CalledProcessError:
        print("[ERROR] Failed while building config from CSVs")
        sys.exit(1)

    if not generated_config.exists():
        print("[ERROR] Config file was not generated:")
        print(generated_config)
        sys.exit(1)

    print("[OK] Generated config:", generated_config)

    # ============================================================
    # STEP 2: Run existing simulation
    # ============================================================

    print("=" * 70)
    print("[STEP 2] Running simulation")
    print("=" * 70)

    run_cmd = [
        sys.executable,
        str(SIM_SCRIPTS / "run_simulation.py"),
        "--config",
        str(generated_config),
        "--outdir",
        str(outdir),
    ]

    try:
        subprocess.run(
            run_cmd,
            cwd=str(ROOT),
            check=True,
        )
    except subprocess.CalledProcessError:
        print("[ERROR] Simulation failed")
        sys.exit(1)

    print("=" * 70)
    print("[SUCCESS] Full pipeline completed")
    print("Outputs written to:", outdir)
    print("=" * 70)


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":
    main()
