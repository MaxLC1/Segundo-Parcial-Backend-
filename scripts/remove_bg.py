import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image
from sqlalchemy import create_engine, text

def remove_white_bg(img_path, output_path):
    try:
        img = Image.open(img_path).convert('RGBA')
        datas = img.getdata()
        newData = []
        for item in datas:
            if item[0] > 230 and item[1] > 230 and item[2] > 230:
                newData.append((255, 255, 255, 0))
            else:
                newData.append(item)
        img.putdata(newData)
        img.save(output_path, 'PNG')
        return True
    except Exception as e:
        print(f"Error procesando {img_path}: {e}")
        return False

def main():
    DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/fashionstore_ar"
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT id, imagen_url FROM productos WHERE imagen_url IS NOT NULL"))
        productos = result.fetchall()
        
        for pid, img_url in productos:
            if '/uploads/' in img_url:
                filename = img_url.split('/uploads/')[-1]
                filepath = os.path.join('uploads', filename)
                
                if os.path.exists(filepath):
                    name, ext = os.path.splitext(filename)
                    if ext.lower() == '.png':
                        print(f"El producto {pid} ya es PNG, procesando...")
                        new_filename = filename
                    else:
                        new_filename = f"{name}_nobg.png"
                    
                    new_filepath = os.path.join('uploads', new_filename)
                    
                    if remove_white_bg(filepath, new_filepath):
                        # Reconstruir la URL
                        base_url = img_url.split('/uploads/')[0]
                        new_url = f"{base_url}/uploads/{new_filename}"
                        conn.execute(text("UPDATE productos SET imagen_url = :url WHERE id = :id"), {"url": new_url, "id": pid})
                        conn.commit()
                        print(f"Producto {pid} actualizado a {new_filename}")

if __name__ == '__main__':
    main()
