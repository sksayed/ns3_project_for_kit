#!/usr/bin/env python3
import markdown
import weasyprint
import os
import base64
import re
from pathlib import Path

def convert_md_to_pdf(md_file, output_pdf):
    """Convert Markdown file to PDF with embedded images"""
    
    # Read the markdown file
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Get the directory of the markdown file
    md_dir = os.path.dirname(os.path.abspath(md_file))
    
    # Convert images to base64 data URIs
    def embed_images(match):
        alt_text = match.group(1)
        img_path = match.group(2)
        
        # Convert relative paths to absolute paths
        if not os.path.isabs(img_path):
            img_path = os.path.join(md_dir, img_path)
        
        # Check if image exists
        if os.path.exists(img_path):
            try:
                # Read image and convert to base64
                with open(img_path, 'rb') as img_file:
                    img_data = img_file.read()
                    img_base64 = base64.b64encode(img_data).decode('utf-8')
                    
                # Determine MIME type based on file extension
                ext = os.path.splitext(img_path)[1].lower()
                if ext == '.png':
                    mime_type = 'image/png'
                elif ext in ['.jpg', '.jpeg']:
                    mime_type = 'image/jpeg'
                elif ext == '.gif':
                    mime_type = 'image/gif'
                else:
                    mime_type = 'image/png'  # default
                
                # Create data URI
                data_uri = f'data:{mime_type};base64,{img_base64}'
                return f'![{alt_text}]({data_uri})'
            except Exception as e:
                print(f"Error processing image {img_path}: {e}")
                return f'![{alt_text}]({img_path})'
        else:
            print(f"Image not found: {img_path}")
            return f'![{alt_text}]({img_path})'
    
    # Process all images in the markdown
    md_content = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', embed_images, md_content)
    
    # Convert markdown to HTML
    html = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])
    
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
