#!/usr/bin/env python3
import weasyprint
import base64
import os

def test_image_embedding():
    """Test if images can be embedded in PDF"""
    
    # Test with one image
    img_path = "/home/sayed/ns-3-dev/report/network_topology.png"
    
    if os.path.exists(img_path):
        with open(img_path, 'rb') as f:
            img_data = f.read()
            img_base64 = base64.b64encode(img_data).decode('utf-8')
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Image Test</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                img {{ max-width: 100%; height: auto; border: 1px solid #ddd; }}
            </style>
        </head>
        <body>
            <h1>Image Embedding Test</h1>
            <p>This is a test to verify image embedding works:</p>
            <img src="data:image/png;base64,{img_base64}" alt="Network Topology">
            <p>If you can see the image above, embedding is working correctly!</p>
        </body>
        </html>
        """
        
        weasyprint.HTML(string=html_content).write_pdf("/home/sayed/ns-3-dev/report/image_test.pdf")
        print("Image test PDF created: /home/sayed/ns-3-dev/report/image_test.pdf")
    else:
        print(f"Image not found: {img_path}")

if __name__ == "__main__":
    test_image_embedding()
