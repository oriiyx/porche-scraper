import argparse
import asyncio
import json
import logging

from app.scraper.runner import run


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape currently available Porsche Inter Auto vehicles")
    parser.add_argument("--overwrite", action="store_true", help="Re-scrape and replace vehicles already in the database")
    parser.add_argument("--limit", type=int, help="Only process N vehicles (testing; does not mark others unavailable)")
    images = parser.add_mutually_exclusive_group()
    images.add_argument("--download-images", action="store_true", default=None, help="Download image files into the Docker volume")
    images.add_argument("--no-download-images", action="store_false", dest="download_images", help="Store HD image URLs only")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    print(json.dumps(asyncio.run(run(args.overwrite, args.limit, args.download_images)), ensure_ascii=False))


if __name__ == "__main__":
    main()

