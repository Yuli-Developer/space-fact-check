"""Space Fact Check — main entry point."""
import os, sys, logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/pipeline.log", mode="a"),
    ],
)

if __name__ == "__main__":
    args   = sys.argv[1:]
    upload = "--no-upload" not in args
    style  = None
    if "--style" in args:
        idx   = args.index("--style")
        style = args[idx + 1] if idx + 1 < len(args) else None

    from pipeline.orchestrator import run_full_pipeline
    result = run_full_pipeline(upload=upload, narrator_style=style)

    print(f"\n{'='*60}")
    print(f"Title:  {result.get('title', 'N/A')}")
    print(f"Score:  {result.get('viral_score', 0):.1f}/10")
    print(f"Style:  {result.get('style', 'N/A')}")
    if result.get("shorts_url"):
        print(f"Shorts: {result['shorts_url']}")
    print("="*60)
