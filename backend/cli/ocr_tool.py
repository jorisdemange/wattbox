#!/usr/bin/env python3
"""
OCR Testing CLI Tool

Command-line tool for testing and benchmarking OCR functionality offline.
Perfect for iterating on OCR algorithms without running the full application.

Usage:
    python ocr_tool.py test <image_path> [--strategy STRATEGY]
    python ocr_tool.py batch <folder_path> [--strategy STRATEGY] [--output OUTPUT]
    python ocr_tool.py benchmark <image_path> [--output OUTPUT]
    python ocr_tool.py batch-benchmark <folder_path> [--output OUTPUT]

Examples:
    # Test single image with auto strategy
    python ocr_tool.py test meter_photo.jpg

    # Test with specific strategy
    python ocr_tool.py test meter_photo.jpg --strategy seven_segment

    # Benchmark all strategies on one image
    python ocr_tool.py benchmark meter_photo.jpg --output results.json

    # Test all images in a folder
    python ocr_tool.py batch ./test_images/ --output batch_results.csv

    # Benchmark all images in a folder
    python ocr_tool.py batch-benchmark ./test_images/ --output benchmark_results.json
"""

import argparse
import sys
import os
import json
import csv
from pathlib import Path
from typing import List, Dict, Any
import logging
from tabulate import tabulate
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.ocr_orchestrator import OCROrchestrator, OCRStrategy
from config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OCRTool:
    """CLI tool for OCR testing"""

    def __init__(self):
        settings = get_settings()
        self.orchestrator = OCROrchestrator(settings.TESSERACT_PATH)

    def test_single(self, image_path: str, strategy: str = "auto") -> Dict[str, Any]:
        """
        Test OCR on a single image.

        Args:
            image_path: Path to the image file
            strategy: OCR strategy to use

        Returns:
            Dictionary with test results
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        try:
            ocr_strategy = OCRStrategy(strategy)
        except ValueError:
            raise ValueError(f"Invalid strategy: {strategy}. "
                           f"Must be one of: {[s.value for s in OCRStrategy]}")

        logger.info(f"Testing {image_path} with strategy: {strategy}")

        result = self.orchestrator.extract_reading(image_path, ocr_strategy)

        return {
            'image': image_path,
            'reading_kwh': result.reading_kwh,
            'confidence': result.confidence,
            'strategy_used': result.strategy_used,
            'meter_type': result.meter_type,
            'processing_time_ms': result.processing_time_ms,
            'success': result.success,
            'error_message': result.error_message
        }

    def benchmark_single(self, image_path: str) -> Dict[str, Any]:
        """
        Benchmark all strategies on a single image.

        Args:
            image_path: Path to the image file

        Returns:
            Dictionary with benchmark results
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        logger.info(f"Benchmarking all strategies on {image_path}")

        results = self.orchestrator.benchmark_strategies(image_path)

        # Convert to serializable format
        benchmark_data = {
            'image': image_path,
            'timestamp': datetime.now().isoformat(),
            'strategies': {}
        }

        for strategy_name, result in results.items():
            benchmark_data['strategies'][strategy_name] = result.to_dict()

        # Find best result
        best_strategy = None
        best_confidence = 0.0

        for strategy_name, result in results.items():
            if result.success and result.confidence > best_confidence:
                best_strategy = strategy_name
                best_confidence = result.confidence

        benchmark_data['best_strategy'] = best_strategy
        benchmark_data['best_confidence'] = best_confidence

        return benchmark_data

    def batch_test(self, folder_path: str, strategy: str = "auto") -> List[Dict[str, Any]]:
        """
        Test OCR on all images in a folder.

        Args:
            folder_path: Path to folder containing images
            strategy: OCR strategy to use

        Returns:
            List of test results
        """
        if not os.path.isdir(folder_path):
            raise NotADirectoryError(f"Not a directory: {folder_path}")

        # Find all image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
        image_files = []

        for ext in image_extensions:
            image_files.extend(Path(folder_path).glob(f'*{ext}'))
            image_files.extend(Path(folder_path).glob(f'*{ext.upper()}'))

        if not image_files:
            raise ValueError(f"No image files found in {folder_path}")

        logger.info(f"Found {len(image_files)} images in {folder_path}")

        results = []
        for i, image_file in enumerate(image_files, 1):
            logger.info(f"Processing image {i}/{len(image_files)}: {image_file.name}")
            try:
                result = self.test_single(str(image_file), strategy)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to process {image_file}: {e}")
                results.append({
                    'image': str(image_file),
                    'reading_kwh': None,
                    'confidence': 0.0,
                    'success': False,
                    'error_message': str(e)
                })

        return results

    def batch_benchmark(self, folder_path: str) -> List[Dict[str, Any]]:
        """
        Benchmark all strategies on all images in a folder.

        Args:
            folder_path: Path to folder containing images

        Returns:
            List of benchmark results
        """
        if not os.path.isdir(folder_path):
            raise NotADirectoryError(f"Not a directory: {folder_path}")

        # Find all image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
        image_files = []

        for ext in image_extensions:
            image_files.extend(Path(folder_path).glob(f'*{ext}'))
            image_files.extend(Path(folder_path).glob(f'*{ext.upper()}'))

        if not image_files:
            raise ValueError(f"No image files found in {folder_path}")

        logger.info(f"Benchmarking {len(image_files)} images")

        results = []
        for i, image_file in enumerate(image_files, 1):
            logger.info(f"Benchmarking image {i}/{len(image_files)}: {image_file.name}")
            try:
                result = self.benchmark_single(str(image_file))
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to benchmark {image_file}: {e}")

        return results

    def print_test_result(self, result: Dict[str, Any]):
        """Print test result in a nice format"""
        print("\n" + "=" * 70)
        print(f"Image: {result['image']}")
        print("=" * 70)

        if result['success']:
            print(f"✓ SUCCESS")
            print(f"Reading:     {result['reading_kwh']} kWh")
            print(f"Confidence:  {result['confidence']:.2f}%")
            print(f"Strategy:    {result['strategy_used']}")
            print(f"Meter Type:  {result.get('meter_type', 'N/A')}")
            print(f"Time:        {result['processing_time_ms']:.2f}ms")
        else:
            print(f"✗ FAILED")
            print(f"Error: {result.get('error_message', 'Unknown error')}")

    def print_benchmark_result(self, result: Dict[str, Any]):
        """Print benchmark result in a nice format"""
        print("\n" + "=" * 70)
        print(f"Benchmark: {result['image']}")
        print("=" * 70)

        # Prepare table data
        table_data = []
        for strategy_name, strategy_result in result['strategies'].items():
            table_data.append([
                strategy_name,
                f"{strategy_result['reading_kwh']}" if strategy_result['reading_kwh'] else "FAILED",
                f"{strategy_result['confidence']:.2f}%",
                f"{strategy_result['processing_time_ms']:.2f}ms",
                "✓" if strategy_result['success'] else "✗"
            ])

        print(tabulate(
            table_data,
            headers=['Strategy', 'Reading (kWh)', 'Confidence', 'Time', 'Success'],
            tablefmt='grid'
        ))

        print(f"\nBest Strategy: {result.get('best_strategy', 'none')}")
        print(f"Best Confidence: {result.get('best_confidence', 0.0):.2f}%")

    def save_results_json(self, results: Any, output_file: str):
        """Save results to JSON file"""
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {output_file}")

    def save_results_csv(self, results: List[Dict[str, Any]], output_file: str):
        """Save batch test results to CSV file"""
        if not results:
            logger.warning("No results to save")
            return

        # Extract keys from first result
        keys = ['image', 'reading_kwh', 'confidence', 'strategy_used',
               'meter_type', 'processing_time_ms', 'success', 'error_message']

        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for result in results:
                # Only write keys that exist
                row = {k: result.get(k, '') for k in keys}
                writer.writerow(row)

        logger.info(f"Results saved to {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='OCR Testing CLI Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Test command
    test_parser = subparsers.add_parser('test', help='Test OCR on single image')
    test_parser.add_argument('image', help='Path to image file')
    test_parser.add_argument('--strategy', default='auto',
                            help='OCR strategy to use (default: auto)')

    # Benchmark command
    benchmark_parser = subparsers.add_parser('benchmark',
                                            help='Benchmark all strategies on single image')
    benchmark_parser.add_argument('image', help='Path to image file')
    benchmark_parser.add_argument('--output', help='Output file for results (JSON)')

    # Batch test command
    batch_parser = subparsers.add_parser('batch', help='Test OCR on all images in folder')
    batch_parser.add_argument('folder', help='Path to folder containing images')
    batch_parser.add_argument('--strategy', default='auto',
                            help='OCR strategy to use (default: auto)')
    batch_parser.add_argument('--output', help='Output file for results (CSV or JSON)')

    # Batch benchmark command
    batch_benchmark_parser = subparsers.add_parser('batch-benchmark',
                                                   help='Benchmark all strategies on all images')
    batch_benchmark_parser.add_argument('folder', help='Path to folder containing images')
    batch_benchmark_parser.add_argument('--output', help='Output file for results (JSON)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    tool = OCRTool()

    try:
        if args.command == 'test':
            result = tool.test_single(args.image, args.strategy)
            tool.print_test_result(result)

        elif args.command == 'benchmark':
            result = tool.benchmark_single(args.image)
            tool.print_benchmark_result(result)

            if args.output:
                tool.save_results_json(result, args.output)

        elif args.command == 'batch':
            results = tool.batch_test(args.folder, args.strategy)

            # Print summary
            successful = sum(1 for r in results if r['success'])
            print(f"\n{'=' * 70}")
            print(f"Batch Test Summary")
            print(f"{'=' * 70}")
            print(f"Total images:     {len(results)}")
            print(f"Successful:       {successful}")
            print(f"Failed:           {len(results) - successful}")
            print(f"Success rate:     {successful / len(results) * 100:.1f}%")

            if args.output:
                if args.output.endswith('.json'):
                    tool.save_results_json(results, args.output)
                else:
                    tool.save_results_csv(results, args.output)

        elif args.command == 'batch-benchmark':
            results = tool.batch_benchmark(args.folder)

            # Print summary
            print(f"\n{'=' * 70}")
            print(f"Batch Benchmark Summary")
            print(f"{'=' * 70}")
            print(f"Total images benchmarked: {len(results)}")

            if args.output:
                tool.save_results_json(results, args.output)

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
