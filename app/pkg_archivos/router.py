from fastapi import APIRouter, UploadFile, File, HTTPException
import shutil
import os
import uuid
import base64
import requests
from app.core.config import settings

router = APIRouter(tags=["Archivos"])

@router.post("/upload")
def upload_file(file: UploadFile = File(...)):
    # Validar que sea imagen o modelo 3D
    allowed_extensions = {".jpg", ".jpeg", ".png", ".webp", ".glb", ".gltf"}
    ext = os.path.splitext(file.filename)[1].lower()
    
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Formato de archivo no soportado")
    
    # Generar un nombre único
    unique_filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join("uploads", unique_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Si es imagen, intentamos quitarle el fondo blanco automáticamente
    if ext in {".jpg", ".jpeg", ".png", ".webp"}:
        try:
            from PIL import Image
            img = Image.open(file_path).convert('RGBA')
            datas = img.getdata()
            newData = []
            for item in datas:
                if item[0] > 230 and item[1] > 230 and item[2] > 230:
                    newData.append((255, 255, 255, 0))
                else:
                    newData.append(item)
            img.putdata(newData)
            
            # Guardar siempre como PNG para soportar transparencia
            png_filename = f"{uuid.uuid4()}_nobg.png"
            png_path = os.path.join("uploads", png_filename)
            img.save(png_path, 'PNG')
            
            # Borrar original y devolver la procesada
            os.remove(file_path)
            unique_filename = png_filename
        except Exception as e:
            print(f"Error quitando fondo: {e}")
            pass # Si falla, dejamos la imagen original

    return {"url": f"{settings.API_BASE_URL}/uploads/{unique_filename}"}

@router.get("/proxy-imagen")
def proxy_imagen(url: str):
    """
    Descarga una imagen remota y la devuelve en Base64 para evitar problemas de CORS en canvas.
    Si la URL es de uploads local, la lee directamente.
    """
    try:
        if "uploads/" in url and not url.startswith("http"):
            file_path = url
        elif "uploads/" in url and url.startswith("http"):
            file_path = url.split("uploads/")[1]
            file_path = os.path.join("uploads", file_path)
        else:
            response = requests.get(url)
            if response.status_code == 200:
                base64_data = base64.b64encode(response.content).decode("utf-8")
                mime = response.headers.get("Content-Type", "image/png")
                return {"base64": f"data:{mime};base64,{base64_data}"}
            else:
                raise HTTPException(status_code=400, detail="No se pudo descargar la imagen")
                
        # Lectura local si era de uploads/
        if os.path.exists(file_path):
            with open(file_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
                ext = os.path.splitext(file_path)[1].lower()
                mime = f"image/{ext.replace('.', '')}"
                if mime == "image/jpg": mime = "image/jpeg"
                return {"base64": f"data:{mime};base64,{encoded_string}"}
        else:
            raise HTTPException(status_code=404, detail="Imagen local no encontrada")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi.responses import Response
from io import BytesIO

@router.get("/proxy-nobg")
def proxy_nobg(url: str):
    """
    Descarga una imagen (o lee de uploads) y le quita el fondo blanco al vuelo.
    """
    try:
        if "uploads/" in url and not url.startswith("http"):
            file_path = url
        elif "uploads/" in url and url.startswith("http"):
            file_path = url.split("uploads/")[1]
            file_path = os.path.join("uploads", file_path)
        else:
            raise HTTPException(status_code=400, detail="Solo se soportan imágenes locales para nobg")
            
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Imagen local no encontrada")
            
        from PIL import Image
        img = Image.open(file_path).convert('RGBA')
        datas = img.getdata()
        newData = []
        for item in datas:
            lum = (item[0] + item[1] + item[2]) / 3
            if lum > 240:
                newData.append((item[0], item[1], item[2], 0))
            elif lum > 200:
                alpha = int((240 - lum) / 40 * 255)
                newData.append((item[0], item[1], item[2], alpha))
            else:
                newData.append(item)
        img.putdata(newData)
        
        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        return Response(content=img_byte_arr.getvalue(), media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

