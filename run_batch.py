"""Space Fact Check batch runner."""
import os, sys, time, logging, fcntl

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)
os.makedirs("logs", exist_ok=True)

# Prevent concurrent runs (shorts + longform sharing same lock)
_LOCK_FILE = open(os.path.join(PROJECT_ROOT, ".batch.lock"), "w")
try:
    fcntl.flock(_LOCK_FILE, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    print("space-fact-check: another job is already running — exiting.")
    sys.exit(0)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/batch_cron.log", mode="a"),
    ],
)
logger = logging.getLogger("batch")

from pipeline.orchestrator import run_full_pipeline
from storage.database import init_db


def _run_with_retry(upload: bool, max_retries: int = 3) -> dict:
    delays = [60, 120, 180]
    for attempt in range(max_retries + 1):
        try:
            return run_full_pipeline(upload=upload)
        except Exception as e:
            is_transient = (
                any(x in str(e) for x in ("503", "UNAVAILABLE", "429", "Resource has been exhausted"))
                or type(e).__name__ == "JSONDecodeError"
            )
            if attempt < max_retries and is_transient:
                wait = delays[min(attempt, len(delays) - 1)]
                logger.warning(f"Transient API error (attempt {attempt + 1}/{max_retries}), retrying in {wait}s: {e}")
                time.sleep(wait)
            else:
                raise


def _reset_used():
    import sqlite3
    from config.settings import DB_PATH
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE stories SET used=0")
        conn.commit()
        conn.close()
    except Exception:
        pass


def run_batch(n: int = 3, upload: bool = True):
    print(f"\n{'='*60}\nSPACE FACT CHECK BATCH — {n} videos | upload={upload}\n{'='*60}\n")
    init_db()
    _reset_used()
    results, failed = [], 0

    for i in range(1, n + 1):
        print(f"\nVIDEO {i}/{n}")
        try:
            result = _run_with_retry(upload=upload)
            if "error" in result:
                failed += 1
                logger.warning(f"Video {i} soft-failed: {result['error']}")
                continue
            results.append(result)
            url   = result.get("shorts_url", "no url")
            score = result.get("viral_score", 0)
            print(f"\n✓ Video {i}: {result.get('title','')[:55]}")
            print(f"  Score: {score:.1f}/10 | URL: {url}")
        except Exception as e:
            failed += 1
            logger.error(f"Video {i} failed: {e}")
            time.sleep(30)

        if i < n:
            time.sleep(15)

    print(f"\n{'='*60}")
    print(f"BATCH COMPLETE: {len(results)} ok, {failed} failed")
    for r in results:
        url = r.get("shorts_url", "")
        print(f"  [{r.get('viral_score',0):.1f}] {r.get('title','')[:55]} → {url}")
    print(f"{'='*60}\n")
    return results


if __name__ == "__main__":
    args   = sys.argv[1:]
    n      = 3
    upload = "--no-upload" not in args
    for a in args:
        if a.isdigit():
            n = int(a)
    run_batch(n=n, upload=upload)
