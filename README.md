# Smart File Organizer

A Python-based intelligent file organizer that uses Language Models to understand and categorize your files meaningfully. Instead of just sorting by file extensions, it analyzes filenames to create intuitive groupings and suggests better file names.

## Features

- 🧠 **AI-Powered Organization**: Uses Language Models to understand file context from names
- 🎯 **Smart Categorization**: Automatically groups similar files based on semantic analysis
- 🔄 **Category Merging**: Intelligently merges related categories using keyword similarity
- ✨ **Name Enhancement**: Suggests clearer, more descriptive filenames
- 🔍 **Duplicate Handling**: Automatically handles duplicate filenames
- 🚀 **Dry Run Mode**: Preview organization changes before applying them
- 📊 **Rich Console Output**: Clear, colorful progress tracking and results

## Requirements

```
requests>=2.31.0
PyYAML>=6.0.1
rich>=13.6.0
python-magic>=0.4.27
pathlib>=1.0.1
typing-extensions>=4.8.0
```

## Usage

Basic usage:
```bash
python file_organizer.py
```

Advanced options:
```bash
python file_organizer.py --source /path/to/source --target /path/to/destination --dry-run
```

Arguments:
- `--source`, `-s`: Source directory to organize (default: current directory)
- `--target`, `-t`: Target directory for organized files (default: ./organized)
- `--dry-run`, `-d`: Preview changes without moving files

## How It Works

1. **File Analysis**: Uses LLM to analyze each filename and:
   - Suggest appropriate category
   - Extract relevant keywords
   - Propose clearer filename

2. **Smart Grouping**: 
   - Collects keywords for each category
   - Merges similar categories based on keyword overlap
   - Creates intuitive folder structure

3. **Safe Organization**:
   - Creates category directories
   - Handles naming conflicts
   - Moves files to appropriate locations
   - Provides detailed progress feedback

## Example

```bash
$ python file_organizer.py --source ~/Downloads --dry-run
Analyzing files...
Grouping similar files...
[green]Would move:[/green] lecture1.pdf → Courses/introduction_to_python.pdf
[green]Would move:[/green] img01.jpg → Photography/sunset_beach.jpg
```

## Notes

- Requires a local LLM server running on http://localhost:1234 (LM Studio default endpoint)
- Skips system directories (.git, __pycache__, etc.)
- Logs detailed information about the organization process
