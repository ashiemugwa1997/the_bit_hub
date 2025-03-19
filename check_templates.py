import os
import re

def check_templates_extend_base(templates_dir):
    """Check if all template files extend base.html"""
    issues_found = []
    
    # Pattern to match extends statement
    extends_pattern = r'{%\s*extends\s+[\'"](.+?)[\'"]\s*%}'
    
    # Walk through all template directories
    for root, _, files in os.walk(templates_dir):
        for file in files:
            if file.endswith('.html'):
                # Skip certain files that don't need to extend base
                if file in ['base.html', '_base.html', '_base_focus.html']:
                    continue
                
                filepath = os.path.join(root, file)
                relative_path = os.path.relpath(filepath, templates_dir)
                
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Check if file extends anything
                    extends_match = re.search(extends_pattern, content)
                    
                    if not extends_match:
                        issues_found.append(f"ERROR: {relative_path} doesn't extend any template")
                    elif 'base.html' not in extends_match.group(1) and '_base.html' not in extends_match.group(1):
                        issues_found.append(f"WARNING: {relative_path} extends {extends_match.group(1)} instead of base.html")
    
    return issues_found

if __name__ == "__main__":
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    issues = check_templates_extend_base(templates_dir)
    
    if issues:
        print(f"Found {len(issues)} template issues:")
        for issue in issues:
            print(f"- {issue}")
        print("\nPlease fix these issues to ensure consistent styling.")
    else:
        print("All templates correctly extend base.html!")
