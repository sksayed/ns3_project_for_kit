#!/usr/bin/env python3
import markdown
import weasyprint
import os
from pathlib import Path

def convert_md_to_pdf(md_file, output_pdf):
    """Convert Markdown file to PDF with proper formatting"""
    
    # Read the markdown file
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Get the directory of the markdown file
    md_dir = os.path.dirname(os.path.abspath(md_file))
    
    # Convert relative image paths to absolute paths
    import re
    def fix_image_paths(match):
        alt_text = match.group(1)
        img_path = match.group(2)
        if not os.path.isabs(img_path):
            abs_path = os.path.join(md_dir, img_path)
            return f'![{alt_text}]({abs_path})'
        return match.group(0)
    
    # Fix image paths in markdown content
    md_content = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', fix_image_paths, md_content)
    
    # Convert markdown to HTML
    html = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])
    
    # Wrap images in figure divs for better formatting
    def wrap_images(match):
        img_tag = match.group(0)
        return f'<div class="figure">{img_tag}</div>'
    
    html = re.sub(r'<img[^>]*>', wrap_images, html)
    
    # Add CSS styling for better PDF formatting
    css_style = """
    <style>
    body {
        font-family: Arial, sans-serif;
        line-height: 1.6;
        margin: 40px;
        color: #333;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #2c3e50;
        margin-top: 30px;
        margin-bottom: 15px;
    }
    h1 {
        border-bottom: 2px solid #3498db;
        padding-bottom: 10px;
    }
    h2 {
        border-bottom: 1px solid #bdc3c7;
        padding-bottom: 5px;
    }
    table {
        border-collapse: collapse;
        width: 100%;
        margin: 20px 0;
    }
    th, td {
        border: 1px solid #ddd;
        padding: 12px;
        text-align: left;
    }
    th {
        background-color: #f2f2f2;
        font-weight: bold;
    }
    img {
        max-width: 100%;
        height: auto;
        display: block;
        margin: 20px auto;
        border: 1px solid #ddd;
        padding: 10px;
        background-color: #f9f9f9;
        page-break-inside: avoid;
    }
    .figure {
        text-align: center;
        margin: 20px 0;
        page-break-inside: avoid;
    }
    .figure img {
        margin: 10px auto;
    }
    .figure p {
        font-style: italic;
        color: #666;
        margin-top: 10px;
    }
    code {
        background-color: #f4f4f4;
        padding: 2px 4px;
        border-radius: 3px;
        font-family: 'Courier New', monospace;
    }
    pre {
        background-color: #f4f4f4;
        padding: 15px;
        border-radius: 5px;
        overflow-x: auto;
    }
    blockquote {
        border-left: 4px solid #3498db;
        margin: 20px 0;
        padding-left: 20px;
        color: #666;
    }
    .page-break {
        page-break-before: always;
    }
    </style>
    """
    
    # Create complete HTML document
    html_doc = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Network Simulation Analysis Report</title>
        {css_style}
    </head>
    <body>
        {html}
    </body>
    </html>
    """
    
    # Convert HTML to PDF
    weasyprint.HTML(string=html_doc).write_pdf(output_pdf)
    print(f"Successfully converted {md_file} to {output_pdf}")

if __name__ == "__main__":
    md_file = "/home/sayed/ns-3-dev/report/Network_Simulation_Analysis_Report.md"
    output_pdf = "/home/sayed/ns-3-dev/report/Network_Simulation_Analysis_Report.pdf"
    
    if os.path.exists(md_file):
        convert_md_to_pdf(md_file, output_pdf)
        print(f"PDF report created: {output_pdf}")
    else:
        print(f"Error: Markdown file not found: {md_file}")
