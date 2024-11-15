import os
import shutil
import logging
from pathlib import Path
import requests
from typing import Dict, List, Tuple
from rich.console import Console
from rich.progress import track
import re
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class SmartFileOrganizer:
    def __init__(self):
        """Initialize the SmartFileOrganizer"""
        self.console = Console()
        self.llm_url = "http://localhost:1234/v1/chat/completions"  # LM Studio default endpoint
        self.category_map = {}  # Maps specific categories to general ones
        self.category_keywords = defaultdict(list)  # Collects keywords for each category

    def analyze_filename(self, filename: str) -> Tuple[str, str, List[str]]:
        """
        Query LLM to analyze filename and suggest category and new name
        Returns: (category, new_name, keywords)
        """
        name, ext = os.path.splitext(filename)
        
        prompt = f"""
        Analyze this filename: {name}
        
        Task 1: Suggest a very general category (1-2 words max) for what type of file this is.
        Think broad categories like: GameDev, WebDev, Documents, Media, etc.
        
        Task 2: List 3-5 keywords that describe what this file is about.
        These will be used to group similar files together.
        
        Task 3: Suggest a clearer, more descriptive name for this file.
        
        Respond in exactly this format:
        CATEGORY: your_category
        KEYWORDS: keyword1, keyword2, keyword3
        NEWNAME: your_suggested_name
        """
        
        try:
            response = requests.post(
                self.llm_url,
                json={
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 150
                },
                timeout=10
            )
            response.raise_for_status()
            result = response.json()['choices'][0]['message']['content']
            
            # Parse response
            category_match = re.search(r'CATEGORY:\s*(.+)', result)
            keywords_match = re.search(r'KEYWORDS:\s*(.+)', result)
            name_match = re.search(r'NEWNAME:\s*(.+)', result)
            
            category = category_match.group(1).strip() if category_match else "Misc"
            keywords = [k.strip() for k in keywords_match.group(1).split(',')] if keywords_match else []
            new_name = name_match.group(1).strip() if name_match else name
            
            # Clean up category and new name
            category = re.sub(r'[<>:"/\\|?*]', '', category)
            new_name = re.sub(r'[<>:"/\\|?*]', '', new_name)
            
            return category, f"{new_name}{ext}", keywords
            
        except Exception as e:
            logger.error(f"Error analyzing filename {filename}: {e}")
            return "Misc", filename, []

    def merge_categories(self, file_data: List[Tuple[Path, str, str, List[str]]]) -> Dict[str, List[Tuple[Path, str]]]:
        """
        Analyze all files and their keywords to create sensible groupings
        Returns: Dict[category_name, List[Tuple[source_path, new_name]]]
        """
        # First, collect all keywords for each initial category
        category_keywords = defaultdict(set)
        for _, category, _, keywords in file_data:
            category_keywords[category].update(keywords)

        # Find similar categories based on keyword overlap
        merged_categories = defaultdict(list)
        processed_categories = set()

        for cat1, keywords1 in category_keywords.items():
            if cat1 in processed_categories:
                continue

            similar_cats = [cat1]
            for cat2, keywords2 in category_keywords.items():
                if cat2 != cat1 and cat2 not in processed_categories:
                    # Calculate keyword similarity
                    similarity = len(keywords1.intersection(keywords2)) / len(keywords1.union(keywords2))
                    if similarity > 0.3:  # Adjust threshold as needed
                        similar_cats.append(cat2)

            # Merge similar categories
            merged_name = self.get_merged_category_name(similar_cats)
            for cat in similar_cats:
                processed_categories.add(cat)
                for file_path, category, new_name, _ in file_data:
                    if category == cat:
                        merged_categories[merged_name].append((file_path, new_name))

        return merged_categories

    def get_merged_category_name(self, categories: List[str]) -> str:
        """Generate a suitable name for merged categories"""
        if len(categories) == 1:
            return categories[0]

        # Ask LLM to suggest a common category name
        categories_str = ", ".join(categories)
        prompt = f"""
        These categories appear to be related: {categories_str}
        Suggest a single, general category name (1-2 words) that would encompass all of them.
        Respond with just the category name, nothing else.
        """

        try:
            response = requests.post(
                self.llm_url,
                json={
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 50
                },
                timeout=10
            )
            response.raise_for_status()
            merged_name = response.json()['choices'][0]['message']['content'].strip()
            return re.sub(r'[<>:"/\\|?*]', '', merged_name)
        except Exception as e:
            logger.error(f"Error getting merged category name: {e}")
            return categories[0]

    def organize_files(self, source_dir: str, target_dir: str, dry_run: bool = False) -> Dict:
        """Organize files from source directory into target directory"""
        source_path = Path(source_dir).resolve()
        target_path = Path(target_dir).resolve()
        stats = {"processed": 0, "moved": 0, "errors": 0}
        
        if not dry_run:
            target_path.mkdir(parents=True, exist_ok=True)

        # Collect all files and their analysis
        self.console.print("[yellow]Analyzing files...[/yellow]")
        all_file_data = []
        for file_path in source_path.rglob("*"):
            if file_path.is_file() and not any(p in str(file_path) for p in ['.git', '__pycache__', '.pytest_cache']):
                category, new_name, keywords = self.analyze_filename(file_path.name)
                all_file_data.append((file_path, category, new_name, keywords))
                stats["processed"] += 1

        # Merge categories and organize files
        self.console.print("[yellow]Grouping similar files...[/yellow]")
        merged_categories = self.merge_categories(all_file_data)

        # Move files to their final locations
        for category, files in track(merged_categories.items(), description="Organizing files"):
            category_path = target_path / category
            
            if not dry_run:
                category_path.mkdir(parents=True, exist_ok=True)

            for source_path, new_name in files:
                try:
                    new_file_path = category_path / new_name
                    
                    # Handle duplicate filenames
                    counter = 1
                    while new_file_path.exists():
                        name_parts = os.path.splitext(new_name)
                        new_file_path = category_path / f"{name_parts[0]}_{counter}{name_parts[1]}"
                        counter += 1

                    if not dry_run:
                        shutil.move(str(source_path), str(new_file_path))
                        stats["moved"] += 1
                    
                    self.console.print(f"[green]{'Would move' if dry_run else 'Moved'}:[/green] "
                                     f"{source_path.name} → {category}/{new_file_path.name}")
                    
                except Exception as e:
                    logger.error(f"Error moving {source_path}: {e}")
                    stats["errors"] += 1

        return stats

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart File Organizer")
    parser.add_argument("--source", "-s", default=".", help="Source directory to organize")
    parser.add_argument("--target", "-t", default="./organized", help="Target directory for organized files")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Perform a dry run without moving files")
    
    args = parser.parse_args()
    
    organizer = SmartFileOrganizer()
    
    try:
        stats = organizer.organize_files(args.source, args.target, args.dry_run)
        logger.info(f"Organization complete. Stats: {stats}")
    except Exception as e:
        logger.error(f"Organization failed: {e}")
        raise

if __name__ == "__main__":
    main()
