"""
Auto-retry wrapper: runs a command in a loop until it exits with code 0,
or the user presses Ctrl+C.

Usage:
    python run_until_done.py <command> [args...]

Example:
    python run_until_done.py python -m mindeval.scripts.run_eval_matrix \
        --full --eval mind-eval --judge_name claude_9router \
        --settings S3 --max_workers 2 --batch_delay 3
"""
import subprocess
import sys
import time

RETRY_WAIT = 90  # seconds to wait before retrying after a failure


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1:]
    attempt = 0

    print(f"[run_until_done] Command: {' '.join(cmd)}")
    print(f"[run_until_done] Press Ctrl+C to stop.\n")

    while True:
        attempt += 1
        print(f"[run_until_done] --- Attempt {attempt} ---")
        try:
            result = subprocess.run(cmd)
        except KeyboardInterrupt:
            print("\n[run_until_done] Stopped by user (Ctrl+C).")
            sys.exit(0)

        if result.returncode == 0:
            print("[run_until_done] ✓ Completed successfully.")
            sys.exit(0)

        print(f"[run_until_done] Exit code {result.returncode}. "
              f"Waiting {RETRY_WAIT}s before retry (Ctrl+C to stop)...")
        try:
            for remaining in range(RETRY_WAIT, 0, -5):
                print(f"  retrying in {remaining}s...", end="\r")
                time.sleep(5)
            print()
        except KeyboardInterrupt:
            print("\n[run_until_done] Stopped by user (Ctrl+C).")
            sys.exit(0)


if __name__ == "__main__":
    main()
