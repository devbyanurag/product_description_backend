from fastapi import APIRouter, UploadFile, File, Form
from app.services.content_generation_service import generate_img_desc, generate_openai_content, generate_mixtral_content, remove_s_tag
from PIL import Image
from app.utils.helper import CustomErrorResponse, ocr_paddle
from app.utils.constants import ResponseValues
from io import BytesIO
import time
import numpy as np
import pytesseract
import threading
import numpy as np

pytesseract.pytesseract.tesseract_cmd = r'C:\Users\anuragchhetri\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

router = APIRouter()
from typing import List


@router.post("/product-content-generator/mistral")
async def product_desc(files: List[UploadFile] = File(None), 
                     title_word_limit: str = Form('50'),
                     description_word_limit: str = Form('100'),
                     title: str = Form('false'),
                     description: str = Form('false'),
                     category: str = Form(None),
                     language: str = Form('English'),
                     product_context: str = Form(None)):
    try:
        if not files and not product_context:
            return CustomErrorResponse.generate_response("Invalid Input", "No files or product context provided", 400)
        
        if title != 'true' and description != 'true':
            return CustomErrorResponse.generate_response("Invalid Input", "Title/Description one should be true", 400)
        
        text_objects_images_ocr_string = ""
        objects_images_string = ""
        objects_descriptions = []
        text_objects_images_ocr_values = []
        total_processing_time = 0  
        if files is not None:
            for file in files:
                if file.filename == "":
                    return CustomErrorResponse.generate_response("Invalid Input", "File name cannot be empty", 400)
                
                start_time = time.time()
                img = Image.open(BytesIO(await file.read())).convert("RGB")
                result = ocr_paddle.ocr(np.array(img))
                finaltext = ""
                if result[0]:
                    for i in range(len(result[0])):
                        if result[0][i][1]: 
                            text = result[0][i][1][0]
                            finaltext += ' ' + text  
                    text_objects_images_ocr_values.append(finaltext)        
                    
                image_description = generate_img_desc(img)
                objects_descriptions.append(image_description) 
                end_time = time.time()
                processing_time = end_time - start_time
                total_processing_time += processing_time
                print(f"File: {file}, Processing Time: {processing_time:.2f} seconds")
            text_objects_images_ocr_string = ', '.join(text_objects_images_ocr_values)
            objects_images_string = ', '.join(objects_descriptions)
            print(f"Total Processing Time for all files: {total_processing_time:.2f} seconds")  
        
        
        
        generated_title_response=''
        if title=='true':
            title_prompt='Give me a product title for ecommerce website in '+ str(title_word_limit) + ' words exactly or nearly '
            if category:
                title_prompt += f", this product is of specific category : {category}"
            if product_context:
                title_prompt += f", the context of the product is: {product_context}"
            if objects_images_string:
                title_prompt += f", where the visuals of the product are: {objects_images_string}"
            if text_objects_images_ocr_string:
                title_prompt += f", some more detailed information about the product is: {objects_images_string}"
                
            title_prompt += f" and give the output in {language} language and without any note"
            
            generated_title_response = generate_mixtral_content(title_prompt)          
                    
            
            
        generated_description_response=''    
        if description=='true':
            description_prompt='Give me a product description for ecommerce website in '+ str(description_word_limit) + ' words exactly or nearly '
            if category:
                title_prompt += f", this product is of specific category : {category}"
            if product_context:
                description_prompt += f", the context of the product is: {product_context}"
            if objects_images_string:
                description_prompt += f", where the visuals of the product are: {objects_images_string}"
            if text_objects_images_ocr_string:
                description_prompt += f", some more detailed information about the product is: {objects_images_string}"
                
            description_prompt += f" and give the output in {language} language"
            if category:
                if category=='Electronics':
                    attribute='specifications'
                    description_prompt += f" with a {attribute} points if there. and without any note"
                elif category=='Food':
                    attribute='Nutrition'
                    description_prompt += f" with a {attribute} points if there. and without any note"
            generated_description_response = generate_mixtral_content(description_prompt)   
            
    
        return {
            "status": ResponseValues.SUCCESS,
            "message": "Generated successfully",
            "body": {
                "title": remove_s_tag(generated_title_response),
                "description": remove_s_tag(generated_description_response)
            }
        }
    except Exception as e:
        print(e, "error")
        return CustomErrorResponse.generate_response("Error", str(e), 500)
       
@router.post("/product-content-generator/mistral/threading")
async def product_desc(files: List[UploadFile] = File(None), 
                     title_word_limit: str = Form('50'),
                     description_word_limit: str = Form('100'),
                     title: str = Form('false'),
                     description: str = Form('false'),
                     category: str = Form(None),
                     language: str = Form('English'),
                     product_context: str = Form(None)):
    try:
        if not files and not product_context:
            return CustomErrorResponse.generate_response("Invalid Input", "No files or product context provided", 400)
        
        if title != 'true' and description != 'true':
            return CustomErrorResponse.generate_response("Invalid Input", "Title/Description one should be true", 400)
        
        text_objects_images_ocr_string = ""
        objects_images_string = ""
        objects_descriptions = []
        text_objects_images_ocr_values = []
        total_processing_time = 0  
        def process_file(file):
            img = Image.open(BytesIO(file)).convert("RGB")
            text = pytesseract.image_to_string(img)
            text_objects_images_ocr_values.append(text)
            image_description = generate_img_desc(img)
            objects_descriptions.append(image_description) 
        async def process_files(files):
            threads = []
            for file in files:
                if file.filename == "":
                    return CustomErrorResponse.generate_response("Invalid Input", "File name cannot be empty", 400)
                
                content = await file.read()
                thread = threading.Thread(target=process_file, args=(content,))
                thread.start()
                threads.append(thread)
            
            for thread in threads:
                thread.join()
        
        start_time = time.time()
        await process_files(files)
        end_time = time.time()
        total_processing_time = end_time - start_time
        print(f"Total Processing Time for all files: {total_processing_time:.2f} seconds")  

        text_objects_images_ocr_string = ', '.join(text_objects_images_ocr_values)
        objects_images_string = ', '.join(objects_descriptions)
        
        
        generated_title_response=''
        if title=='true':
            title_prompt='Give me a product title for ecommerce website in '+ str(title_word_limit) + ' words exactly or nearly '
            if category:
                title_prompt += f", this product is of specific category : {category}"
            if product_context:
                title_prompt += f", the context of the product is: {product_context}"
            if objects_images_string:
                title_prompt += f", where the visuals of the product are: {objects_images_string}"
            if text_objects_images_ocr_string:
                title_prompt += f", some more detailed information about the product is: {objects_images_string}"
                
            title_prompt += f" and give the output in {language} language and without any note"
            
            generated_title_response = generate_mixtral_content(title_prompt)          
                    
            
            
        generated_description_response=''    
        if description=='true':
            description_prompt='Give me a product description for ecommerce website in '+ str(description_word_limit) + ' words exactly or nearly '
            if category:
                title_prompt += f", this product is of specific category : {category}"
            if product_context:
                description_prompt += f", the context of the product is: {product_context}"
            if objects_images_string:
                description_prompt += f", where the visuals of the product are: {objects_images_string}"
            if text_objects_images_ocr_string:
                description_prompt += f", some more detailed information about the product is: {objects_images_string}"
                
            description_prompt += f" and give the output in {language} language"
            if category:
                if category=='Electronics':
                    attribute='specifications'
                    description_prompt += f" with a {attribute} points if there. and without any note"
                elif category=='Food':
                    attribute='Nutrition'
                    description_prompt += f" with a {attribute} points if there. and without any note"
            generated_description_response = generate_mixtral_content(description_prompt)   
            
    
        return {
            "status": ResponseValues.SUCCESS,
            "message": "Generated successfully",
            "body": {
                "title": remove_s_tag(generated_title_response),
                "description": remove_s_tag(generated_description_response)
            }
        }
    except Exception as e:
        print(e, "error")
        return CustomErrorResponse.generate_response("Error", str(e), 500)
             
       
       
@router.post("/product-content-generator/openai")
async def product_desc(files: List[UploadFile] = File(None), 
                     title_word_limit: str = Form('50'),
                     description_word_limit: str = Form('100'),
                     title: str = Form('false'),
                     description: str = Form('false'),
                     category: str = Form(None),
                     language: str = Form('English'),
                     product_context: str = Form(None)):
    try:
        if not files and not product_context:
            return CustomErrorResponse.generate_response("Invalid Input", "No files or product context provided", 400)
        
        if title != 'true' and description != 'true':
            return CustomErrorResponse.generate_response("Invalid Input", "Title/Description one should be true", 400)
         
        generated_title_response=''
        generated_description_response='' 
        text_objects_images_ocr_string = ""
        objects_images_string = ""
        objects_descriptions = []
        text_objects_images_ocr_values = []
             
        total_processing_time = 0  
        if files is not None:
            for file in files:
                if file.filename == "":
                    return CustomErrorResponse.generate_response("Invalid Input", "File name cannot be empty", 400)
                
                start_time = time.time()
                img = Image.open(BytesIO(await file.read())).convert("RGB")
                result = ocr_paddle.ocr(np.array(img))
                
                finaltext = ""
                if result[0]:
                    for i in range(len(result[0])):
                        if result[0][i][1]: 
                            text = result[0][i][1][0]
                            finaltext += ' ' + text  
                    text_objects_images_ocr_values.append(finaltext)        
                    
                image_description = generate_img_desc(img)
                objects_descriptions.append(image_description) 
                    
                             
                    
                end_time = time.time()
                processing_time = end_time - start_time
                total_processing_time += processing_time
                print(f"File: {file}, Processing Time: {processing_time:.2f} seconds")
            text_objects_images_ocr_string = ', '.join(text_objects_images_ocr_values)
            objects_images_string = ', '.join(objects_descriptions)
            print(f"Total Processing Time for all files: {total_processing_time:.2f} seconds")  
        
        
        if title=='true' and description=='true':
            product_prompt=f'Give a product title and product description of a product in {language} language.'
            if category:
                product_prompt += f", the product is of specific category : {category}"
            if product_context:
                product_prompt += f",with the context of the product is: {product_context}"
            if objects_images_string:
                product_prompt += f", where the visuals of the product are: {objects_images_string}"
            if text_objects_images_ocr_string:
                product_prompt += f", some more detailed information about the product is: {objects_images_string}"
                
            product_prompt += f" give title in above {str(title_word_limit)} words and give description in above {str(description_word_limit)} words"
            format='{"title":"generated_title","description":"generated_description","feature_points":["generated_feature_point_1","generated_feature_point_2","generated_feature_point_3",...]}'
            product_prompt += f" in this json format:{format}"
            generated_response = generate_openai_content(product_prompt)
            generated_title_response = generated_response['title']
            generated_description_response = generated_response['description']
            feature_points = generated_response['feature_points']
            numbered_feature_points = [f"{i+1}. {point}" for i, point in enumerate(feature_points)]
            generated_description_response = generated_description_response + '\n\nFeature Points:\n' + '\n'.join(numbered_feature_points)
            
        elif title=='true':
            product_prompt=f'Give a product title in {language} language.'
            if category:
                product_prompt += f", the product is of specific category : {category}"
            if product_context:
                product_prompt += f",with the context of the product is: {product_context}"
            if objects_images_string:
                product_prompt += f", where the visuals of the product are: {objects_images_string}"
            if text_objects_images_ocr_string:
                product_prompt += f", some more detailed information about the product is: {objects_images_string}"
                
            product_prompt += f" give title in above {str(title_word_limit)} words"
            format='{"title":"generated_title"}'
            product_prompt += f" in this json format:{format}"
            generated_response = generate_openai_content(product_prompt)
            generated_title_response = generated_response['title']
            
        elif description=='true':
            product_prompt=f'Give a product description in {language} language.'
            if category:
                product_prompt += f", the product is of specific category : {category}"
            if product_context:
                product_prompt += f",with the context of the product is: {product_context}"
            if objects_images_string:
                product_prompt += f", where the visuals of the product are: {objects_images_string}"
            if text_objects_images_ocr_string:
                product_prompt += f", some more detailed information about the product is: {objects_images_string}"
                
            product_prompt += f" give title in above {str(title_word_limit)} words"
            format='{"description":"generated_description","feature_points":["generated_feature_point_1","generated_feature_point_2","generated_feature_point_3",...]}'
            product_prompt += f" in this json format:{format}" 
            generated_response = generate_openai_content(product_prompt)
            generated_description_response = generated_response['description']
            feature_points = generated_response['feature_points']
            numbered_feature_points = [f"{i+1}. {point}" for i, point in enumerate(feature_points)]
            generated_description_response = generated_description_response + '\n\nFeature Points:\n' + '\n'.join(numbered_feature_points)
            
        
                
        return {
            "status": ResponseValues.SUCCESS,
            "message": "Generated successfully",
            "body": {
                "title": generated_title_response,
                "description": generated_description_response
            }
        }
    except Exception as e:
        print(e, "error")
        return CustomErrorResponse.generate_response("Error", str(e), 500)

@router.post("/product-content-generator/openai/threading")
async def product_desc(files: List[UploadFile] = File(None), 
                     title_word_limit: str = Form('50'),
                     description_word_limit: str = Form('100'),
                     title: str = Form('false'),
                     description: str = Form('false'),
                     category: str = Form(None),
                     language: str = Form('English'),
                     product_context: str = Form(None)):
    try:
        if not files and not product_context:
            return CustomErrorResponse.generate_response("Invalid Input", "No files or product context provided", 400)
        
        if title != 'true' and description != 'true':
            return CustomErrorResponse.generate_response("Invalid Input", "Title/Description one should be true", 400)
        
        text_objects_images_ocr_string = ""
        objects_images_string = ""
        objects_descriptions = []
        text_objects_images_ocr_values = []
        total_processing_time = 0
        
        def process_file(file):
            img = Image.open(BytesIO(file)).convert("RGB")
            text = pytesseract.image_to_string(img)
            text_objects_images_ocr_values.append(text)
            image_description = generate_img_desc(img)
            objects_descriptions.append(image_description) 
        async def process_files(files):
            threads = []
            for file in files:
                if file.filename == "":
                    return CustomErrorResponse.generate_response("Invalid Input", "File name cannot be empty", 400)
                
                content = await file.read()
                thread = threading.Thread(target=process_file, args=(content,))
                thread.start()
                threads.append(thread)
            
            for thread in threads:
                thread.join()
        
        start_time = time.time()
        await process_files(files)
        end_time = time.time()
        total_processing_time = end_time - start_time
        print(f"Total Processing Time for all files: {total_processing_time:.2f} seconds")  

        text_objects_images_ocr_string = ', '.join(text_objects_images_ocr_values)
        objects_images_string = ', '.join(objects_descriptions)
        
        if title=='true' and description=='true':
            product_prompt=f'Give a product title and product description of a product in {language} language.'
            if category:
                product_prompt += f", the product is of specific category : {category}"
            if product_context:
                product_prompt += f",with the context of the product is: {product_context}"
            if objects_images_string:
                product_prompt += f", where the visuals of the product are: {objects_images_string}"
            if text_objects_images_ocr_string:
                product_prompt += f", some more detailed information about the product is: {objects_images_string}"
                
            product_prompt += f" give title in above {str(title_word_limit)} words and give description in above {str(description_word_limit)} words"
            format='{"title":"generated_title","description":"generated_description","feature_points":["generated_feature_point_1","generated_feature_point_2","generated_feature_point_3",...]}'
            product_prompt += f" in this json format:{format}"
            generated_response = generate_openai_content(product_prompt)
            generated_title_response = generated_response['title']
            generated_description_response = generated_response['description']
            feature_points = generated_response['feature_points']
            numbered_feature_points = [f"{i+1}. {point}" for i, point in enumerate(feature_points)]
            generated_description_response = generated_description_response + '\n\nFeature Points:\n' + '\n'.join(numbered_feature_points)
            
        elif title=='true':
            product_prompt=f'Give a product title in {language} language.'
            if category:
                product_prompt += f", the product is of specific category : {category}"
            if product_context:
                product_prompt += f",with the context of the product is: {product_context}"
            if objects_images_string:
                product_prompt += f", where the visuals of the product are: {objects_images_string}"
            if text_objects_images_ocr_string:
                product_prompt += f", some more detailed information about the product is: {objects_images_string}"
                
            product_prompt += f" give title in above {str(title_word_limit)} words"
            format='{"title":"generated_title"}'
            product_prompt += f" in this json format:{format}"
            generated_response = generate_openai_content(product_prompt)
            generated_title_response = generated_response['title']
            
        elif description=='true':
            product_prompt=f'Give a product description in {language} language.'
            if category:
                product_prompt += f", the product is of specific category : {category}"
            if product_context:
                product_prompt += f",with the context of the product is: {product_context}"
            if objects_images_string:
                product_prompt += f", where the visuals of the product are: {objects_images_string}"
            if text_objects_images_ocr_string:
                product_prompt += f", some more detailed information about the product is: {objects_images_string}"
                
            product_prompt += f" give title in above {str(title_word_limit)} words"
            format='{"description":"generated_description","feature_points":["generated_feature_point_1","generated_feature_point_2","generated_feature_point_3",...]}'
            product_prompt += f" in this json format:{format}" 
            generated_response = generate_openai_content(product_prompt)
            generated_description_response = generated_response['description']
            feature_points = generated_response['feature_points']
            numbered_feature_points = [f"{i+1}. {point}" for i, point in enumerate(feature_points)]
            generated_description_response = generated_description_response + '\n\nFeature Points:\n' + '\n'.join(numbered_feature_points)
            
        print(text_objects_images_ocr_values)
        
                
        return {
            "status": ResponseValues.SUCCESS,
            "message": "Generated successfully",
            "body": {
                "title": generated_title_response,
                "description": generated_description_response
            }
        }
    except Exception as e:
        print(e, "error")
        return CustomErrorResponse.generate_response("Error", str(e), 500)


@router.post("/product-content-generator/openai/mergeimage")
async def product_desc(files: List[UploadFile] = File(None), 
                     title_word_limit: str = Form('50'),
                     description_word_limit: str = Form('100'),
                     title: str = Form('false'),
                     description: str = Form('false'),
                     category: str = Form(None),
                     language: str = Form('English'),
                     product_context: str = Form(None)):
    try:
        if not files and not product_context:
            return CustomErrorResponse.generate_response("Invalid Input", "No files or product context provided", 400)
        
        if title != 'true' and description != 'true':
            return CustomErrorResponse.generate_response("Invalid Input", "Title/Description one should be true", 400)
         
        generated_title_response=''
        generated_description_response='' 
        text_objects_images_ocr_string = ""
        objects_images_string = ""
        objects_descriptions = []
        text_objects_images_ocr_values = []
        
        total_processing_time = 0  
        if files is not None:
            
            start_time = time.time()
            images = [Image.open(BytesIO(await file.read())) for file in files]
            widths, heights = zip(*(i.size for i in images))
            total_width = max(widths)
            total_height = sum(heights)
            new_im = Image.new('RGB', (total_width, total_height))
            y_offset = 0
            for im in images:
                new_im.paste(im, (0, y_offset))
                y_offset += im.size[1]
                
            new_im.save('myimage_500.jpg')
            img = new_im
            result = ocr_paddle.ocr(np.array(img))
            
            finaltext = ""
            if result[0]:
                for i in range(len(result[0])):
                    if result[0][i][1]: 
                        text = result[0][i][1][0]
                        finaltext += ' ' + text  
                text_objects_images_ocr_values.append(finaltext)  
                
            image_description = generate_img_desc(img)
            objects_descriptions.append(image_description) 
            end_time = time.time()
            processing_time = end_time - start_time
            total_processing_time += processing_time
            print(f"File: {img}, Processing Time: {processing_time:.2f} seconds")
            
            text_objects_images_ocr_string = ', '.join(text_objects_images_ocr_values)
            objects_images_string = ', '.join(objects_descriptions)
        
        
        if title=='true' and description=='true':
            product_prompt=f'Give a product title and product description of a product in {language} language.'
            if category:
                product_prompt += f", the product is of specific category : {category}"
            if product_context:
                product_prompt += f",with the context of the product is: {product_context}"
            if objects_images_string:
                product_prompt += f", where the visuals of the product are: {objects_images_string}"
            if text_objects_images_ocr_string:
                product_prompt += f", some more detailed information about the product is: {objects_images_string}"
                
            product_prompt += f" give title in above {str(title_word_limit)} words and give description in above {str(description_word_limit)} words"
            format='{"title":"generated_title","description":"generated_description","feature_points":["generated_feature_point_1","generated_feature_point_2","generated_feature_point_3",...]}'
            product_prompt += f" in this json format:{format}"
            generated_response = generate_openai_content(product_prompt)
            generated_title_response = generated_response['title']
            generated_description_response = generated_response['description']
            feature_points = generated_response['feature_points']
            numbered_feature_points = [f"{i+1}. {point}" for i, point in enumerate(feature_points)]
            generated_description_response = generated_description_response + '\n\nFeature Points:\n' + '\n'.join(numbered_feature_points)
            
        elif title=='true':
            product_prompt=f'Give a product title in {language} language.'
            if category:
                product_prompt += f", the product is of specific category : {category}"
            if product_context:
                product_prompt += f",with the context of the product is: {product_context}"
            if objects_images_string:
                product_prompt += f", where the visuals of the product are: {objects_images_string}"
            if text_objects_images_ocr_string:
                product_prompt += f", some more detailed information about the product is: {objects_images_string}"
                
            product_prompt += f" give title in above {str(title_word_limit)} words"
            format='{"title":"generated_title"}'
            product_prompt += f" in this json format:{format}"
            generated_response = generate_openai_content(product_prompt)
            generated_title_response = generated_response['title']
            
        elif description=='true':
            product_prompt=f'Give a product description in {language} language.'
            if category:
                product_prompt += f", the product is of specific category : {category}"
            if product_context:
                product_prompt += f",with the context of the product is: {product_context}"
            if objects_images_string:
                product_prompt += f", where the visuals of the product are: {objects_images_string}"
            if text_objects_images_ocr_string:
                product_prompt += f", some more detailed information about the product is: {objects_images_string}"
                
            product_prompt += f" give title in above {str(title_word_limit)} words"
            format='{"description":"generated_description","feature_points":["generated_feature_point_1","generated_feature_point_2","generated_feature_point_3",...]}'
            product_prompt += f" in this json format:{format}" 
            generated_response = generate_openai_content(product_prompt)
            generated_description_response = generated_response['description']
            feature_points = generated_response['feature_points']
            numbered_feature_points = [f"{i+1}. {point}" for i, point in enumerate(feature_points)]
            generated_description_response = generated_description_response + '\n\nFeature Points:\n' + '\n'.join(numbered_feature_points)
            
        
                
        return {
            "status": ResponseValues.SUCCESS,
            "message": "Generated successfully",
            "body": {
                "title": generated_title_response,
                "description": generated_description_response
            }
        }
    except Exception as e:
        print(e, "error")
        return CustomErrorResponse.generate_response("Error", str(e), 500)
              

# @router.post("/product-content-generator/openai/seperated")
# async def product_desc(files: List[UploadFile] = File(None), 
#                      title_word_limit: str = Form('50'),
#                      description_word_limit: str = Form('100'),
#                      title: str = Form('false'),
#                      description: str = Form('false'),
#                      category: str = Form(None),
#                      language: str = Form('English'),
#                      product_context: str = Form(None)):
#     try:
#         if not files and not product_context:
#             return CustomErrorResponse.generate_response("Invalid Input", "No files or product context provided", 400)
        
#         if title != 'true' and description != 'true':
#             return CustomErrorResponse.generate_response("Invalid Input", "Title/Description one should be true", 400)
        
#         generated_title_response=''
#         generated_description_response='' 
#         text_objects_images_ocr_string = ""
#         objects_images_string = ""
#         objects_descriptions = []
#         text_objects_images_ocr_values = []
             
#         total_processing_time = 0  
#         if files is not None:
#             for file in files:
#                 if file.filename == "":
#                     return CustomErrorResponse.generate_response("Invalid Input", "File name cannot be empty", 400)
                
#                 start_time = time.time()
#                 img = Image.open(BytesIO(await file.read())).convert("RGB")
#                 result = ocr_paddle.ocr(np.array(img))
#                 finaltext = ""
#                 if result[0]:
#                     for i in range(len(result[0])):
#                         if result[0][i][1]: 
#                             text = result[0][i][1][0]
#                             finaltext += ' ' + text  
#                     text_objects_images_ocr_values.append(finaltext)        
                    
#                 image_description = generate_img_desc(img)
#                 objects_descriptions.append(image_description)      
#                 end_time = time.time()
#                 processing_time = end_time - start_time
#                 total_processing_time += processing_time
#                 print(f"File: {file}, Processing Time: {processing_time:.2f} seconds")
#             text_objects_images_ocr_string = ', '.join(text_objects_images_ocr_values)
#             objects_images_string = ', '.join(objects_descriptions)
             
#         generated_title_response=''
#         if title=='true':
#             title_prompt='Give me a product title for ecommerce website in '+ str(title_word_limit) + ' words exactly or nearly '
#             if category:
#                 title_prompt += f", this product is of specific category : {category}"
#             if product_context:
#                 title_prompt += f", the context of the product is: {product_context}"
#             if objects_images_string:
#                 title_prompt += f", where the visuals of the product are: {objects_images_string}"
#             if text_objects_images_ocr_string:
#                 title_prompt += f", some more detailed information about the product is: {objects_images_string}"
                
#             title_prompt += f" and give the output in {language} language"
#             format='{"title":"generated_title"}'
#             title_prompt += f"  in this json format:{format}"
            
#             generated_title_response = generate_openai_content(title_prompt)         
#             if 'title' in generated_title_response:
#                 result_title = generated_title_response.get('title', 'title not available')
#                 print(result_title)
#             else:
#                 result_title=""
                    
            
#         generated_description_response=''    
#         if description=='true':
#             description_prompt='Give me a product description for ecommerce website in '+ str(description_word_limit) + ' words exactly or nearly '
#             if category:
#                 description_prompt += f", this product is of specific category : {category}"
#             if product_context:
#                 description_prompt += f", the context of the product is: {product_context}"
#             if objects_images_string:
#                 description_prompt += f", where the visuals of the product are: {objects_images_string}"
#             if text_objects_images_ocr_string:
#                 description_prompt += f", some more detailed information about the product is: {objects_images_string}"
                
#             description_prompt += f" and give the output in {language} language"
            
#             if category:
#                 if category=='Electronics':
#                     format='{"description":"generated_description","specifications_points":["generated_specifications_point_1","generated_specifications_point_2","generated_specifications_point_3",...]}'
#                     description_prompt += f" with a Nutrition points in this json format:{format}"
#                 elif category=='Food':
#                     format='{"description":"generated_description","nutrition_points":["generated_nutrition_point_1","generated_nutrition_point_2","generated_nutrition_point_3",...]}'
#                     description_prompt += f" with a Nutrition points in this json format:{format}"
#             else:
#                 format='{"description":"generated_description"}'
#                 description_prompt += f"  in this json format:{format}"
                
                     
#             generated_description_response = generate_openai_content(description_prompt)   
            
#             if 'description' in generated_description_response:
#                 result_description = generated_description_response.get('description', 'Description not available')

#                 if category == 'Electronics' and 'specifications_points' in generated_description_response:
#                     specifications_points = '\n'.join(generated_description_response.get('specifications_points', []))
#                     result_description = f"{result_description}\n\nSpecifications Points:\n{specifications_points}"
#                 elif category == 'Food' and 'nutrition_points' in generated_description_response:
#                     nutrition_points = '\n'.join(generated_description_response.get('nutrition_points', []))
#                     result_description = f"{result_description}\n\nNutrition Points:\n{nutrition_points}"

#                 print(result_description)
#             else:
#                 result_description=''
            
                
#         return {
#             "status": ResponseValues.SUCCESS,
#             "message": "Generated successfully",
#             "body": {
#                 "title": result_title,
#                 "description": result_description
#             }
#         }
#     except Exception as e:
#         print(e, "error")
#         return CustomErrorResponse.generate_response("Error", str(e), 500)
       
# 19-04-24

from fastapi import APIRouter, UploadFile, File, Form
from app.services.content_generation_service import generate_img_desc, generate_openai_content, generate_mixtral_content, remove_s_tag
from PIL import Image
from app.utils.helper import CustomErrorResponse, ocr_paddle
from app.utils.constants import ResponseValues
from io import BytesIO
import time
import numpy as np
import pytesseract
import threading
import numpy as np

pytesseract.pytesseract.tesseract_cmd = r'C:\Users\anuragchhetri\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

router = APIRouter()
from typing import List


@router.post("/product-content-generator/mistral/threading")
async def product_desc(files: List[UploadFile] = File(None), 
                     title_word_limit: str = Form('50'),
                     description_word_limit: str = Form('100'),
                     title: str = Form('false'),
                     description: str = Form('false'),
                     category: str = Form(None),
                     language: str = Form('English'),
                     product_context: str = Form(None)):
    try:
        if not files and not product_context:
            return CustomErrorResponse.generate_response("Invalid Input", "No files or product context provided", 400)
        
        if title != 'true' and description != 'true':
            return CustomErrorResponse.generate_response("Invalid Input", "Title/Description one should be true", 400)
        
        text_objects_images_ocr_string = ""
        objects_images_string = ""
        objects_descriptions = []
        text_objects_images_ocr_values = []
        total_processing_time = 0  
        def process_file(file):
            img = Image.open(BytesIO(file)).convert("RGB")
            text = pytesseract.image_to_string(img)
            text_objects_images_ocr_values.append(text)
            image_description = generate_img_desc(img)
            objects_descriptions.append(image_description) 
        async def process_files(files):
            threads = []
            for file in files:
                if file.filename == "":
                    return CustomErrorResponse.generate_response("Invalid Input", "File name cannot be empty", 400)
                
                content = await file.read()
                thread = threading.Thread(target=process_file, args=(content,))
                thread.start()
                threads.append(thread)
            
            for thread in threads:
                thread.join()
        
        start_time = time.time()
        await process_files(files)
        end_time = time.time()
        total_processing_time = end_time - start_time
        print(f"Total Processing Time for all files: {total_processing_time:.2f} seconds")  

        text_objects_images_ocr_string = ', '.join(text_objects_images_ocr_values)
        objects_images_string = ', '.join(objects_descriptions)
        
        
        generated_title_response=''
        if title=='true':
            title_prompt='Give me a product title for ecommerce website in '+ str(title_word_limit) + ' words exactly or nearly '
            if category:
                title_prompt += f", this product is of specific category : {category}"
            if product_context:
                title_prompt += f", the context of the product is: {product_context}"
            if objects_images_string:
                title_prompt += f", where the visuals of the product are: {objects_images_string}"
            if text_objects_images_ocr_string:
                title_prompt += f", some more detailed information about the product is: {objects_images_string}"
                
            title_prompt += f" and give the output in {language} language and without any note"
            
            generated_title_response = generate_mixtral_content(title_prompt)          
                    
            
            
        generated_description_response=''    
        if description=='true':
            description_prompt='Give me a product description for ecommerce website in '+ str(description_word_limit) + ' words exactly or nearly '
            if category:
                title_prompt += f", this product is of specific category : {category}"
            if product_context:
                description_prompt += f", the context of the product is: {product_context}"
            if objects_images_string:
                description_prompt += f", where the visuals of the product are: {objects_images_string}"
            if text_objects_images_ocr_string:
                description_prompt += f", some more detailed information about the product is: {objects_images_string}"
                
            description_prompt += f" and give the output in {language} language"
            if category:
                if category=='Electronics':
                    attribute='specifications'
                    description_prompt += f" with a {attribute} points if there. and without any note"
                elif category=='Food':
                    attribute='Nutrition'
                    description_prompt += f" with a {attribute} points if there. and without any note"
            generated_description_response = generate_mixtral_content(description_prompt)   
            
    
        return {
            "status": ResponseValues.SUCCESS,
            "message": "Generated successfully",
            "body": {
                "title": remove_s_tag(generated_title_response),
                "description": remove_s_tag(generated_description_response)
            }
        }
    except Exception as e:
        print(e, "error")
        return CustomErrorResponse.generate_response("Error", str(e), 500)
             
       
       
@router.post("/product-content-generator/openai/threading")
async def product_desc(files: List[UploadFile] = File(None), 
                     title_word_limit: str = Form('50'),
                     description_word_limit: str = Form('100'),
                     title: str = Form('false'),
                     description: str = Form('false'),
                     category: str = Form(None),
                     language: str = Form('English'),
                     product_context: str = Form(None)):
    try:
        if not files and not product_context:
            return CustomErrorResponse.generate_response("Invalid Input", "No files or product context provided", 400)
        
        if title != 'true' and description != 'true':
            return CustomErrorResponse.generate_response("Invalid Input", "Title/Description one should be true", 400)
        
        text_objects_images_ocr_string = ""
        objects_images_string = ""
        objects_descriptions = []
        text_objects_images_ocr_values = []
        total_processing_time_textGeneration = 0
        total_processing_time_images=0
        generated_title_response=''
        generated_description_response=''
        
        # OCR part
        # def ocr_and_append(img):
        #     text = pytesseract.image_to_string(img)
        #     text_objects_images_ocr_values.append(text)
        
        # # Description generation part
        # def generate_desc_and_append(img):
        #     image_description = generate_img_desc(img)
        #     objects_descriptions.append(image_description)
        
        # def process_file(file):
        #     img = Image.open(BytesIO(file)).convert("RGB")
            
        #     ocr_and_append(img)

        #     generate_desc_and_append(img)
        
        def process_file(file):
            img = Image.open(BytesIO(file)).convert("RGB")

            def ocr_and_append(img):
                text = pytesseract.image_to_string(img)
                text_objects_images_ocr_values.append(text)

            def generate_desc_and_append(img):
                image_description = generate_img_desc(img)
                objects_descriptions.append(image_description)


            thread_ocr = threading.Thread(target=ocr_and_append, args=(img,))
            thread_desc = threading.Thread(target=generate_desc_and_append, args=(img,))

            thread_ocr.start()
            thread_desc.start()

            thread_ocr.join()
            thread_desc.join()

                
    
        async def process_files(files):
            threads = []
            for file in files:
                if file.filename == "":
                    return CustomErrorResponse.generate_response("Invalid Input", "File name cannot be empty", 400)
                
                content = await file.read()
                thread = threading.Thread(target=process_file, args=(content,))
                thread.start()
                threads.append(thread)
            
            for thread in threads:
                thread.join()
        
        start_time = time.time()
        if files:
            await process_files(files)
          
        end_time = time.time()
        total_processing_time_images = end_time - start_time



        text_objects_images_ocr_string = ', '.join(text_objects_images_ocr_values)
        objects_images_string = ', '.join(objects_descriptions)
        
        
        
        start_time = time.time()
        
        if title=='true' and description=='true':
            product_prompt=f'Give a product title of above {str(title_word_limit)} words and product description in {str(description_word_limit)} in {language} language.'
            if category:
                product_prompt += f", the product is of specific category : {category}"
            if product_context:
                product_prompt += f",with the context of the product is: {product_context}"
            if objects_images_string:
                product_prompt += f", where the visuals of the product are: {objects_images_string}"
            if text_objects_images_ocr_string:
                product_prompt += f", some more detailed information about the product is: {text_objects_images_ocr_string}"
                if category=='Electronics':
                    product_prompt+='add specifications if exists in feature_points'
                elif category=='Food':
                    product_prompt+='add all Nutrition Facts that exists, in feature_points'

            product_prompt += f" product title must be above {str(title_word_limit)} words and product description must be in {str(description_word_limit)} words "
            
            format='{"title":"generated_title","description":"generated_description","feature_points":["generated_feature_point_1","generated_feature_point_2","generated_feature_point_3",...]}'
            product_prompt += f" in this json format:{format}"
            generated_response = generate_openai_content(product_prompt)
            generated_title_response = generated_response['title']
            generated_description_response = generated_response['description']
            feature_points = generated_response['feature_points']
            numbered_feature_points = [f"{i+1}. {point}" for i, point in enumerate(feature_points)]
            generated_description_response = generated_description_response + '\n\nFeature Points:\n' + '\n'.join(numbered_feature_points)
    
        elif title=='true':
            product_prompt=f'Give a product title in around {str(title_word_limit)} words in {language} language.'
            if category:
                product_prompt += f", the product is of {category} category. "
            if product_context:
                product_prompt += f",with the context of the product is: {product_context}"
            if objects_images_string:
                product_prompt += f", where the visuals of the product are: {objects_images_string}"
            if text_objects_images_ocr_string:
                product_prompt += f", some more detailed information about the product is: {text_objects_images_ocr_string}"
                
            product_prompt += f" product title must be above in around {str(title_word_limit)} words "
            format='{"title":"generated_title"}'
            product_prompt += f" in this json format:{format}"
            generated_response = generate_openai_content(product_prompt)
            generated_title_response = generated_response['title']
             
        elif description=='true':
            product_prompt=f'Give a product description in {language} language.'
            if category:
                product_prompt += f", the product is of specific category : {category}"
            if product_context:
                product_prompt += f",with the context of the product is: {product_context}"
            if objects_images_string:
                product_prompt += f", where the visuals of the product are: {objects_images_string}"
            if text_objects_images_ocr_string:
                product_prompt += f", some more detailed information about the product is: {text_objects_images_ocr_string}"
                
            product_prompt += f" give description in around {str(description_word_limit)} words"
            format='{"description":"generated_description","feature_points":["generated_feature_point_1","generated_feature_point_2","generated_feature_point_3",...]}'
            product_prompt += f" in this json format:{format}" 
            generated_response = generate_openai_content(product_prompt)
            generated_description_response = generated_response['description']
            feature_points = generated_response['feature_points']
            numbered_feature_points = [f"{i+1}. {point}" for i, point in enumerate(feature_points)]
            generated_description_response = generated_description_response + '\n\nFeature Points:\n' + '\n'.join(numbered_feature_points)
            
        end_time = time.time()
        total_processing_time_textGeneration = end_time - start_time
         
        return {
            "status": ResponseValues.SUCCESS,
            "message": "Generated successfully",
            "body": {
                "title": generated_title_response,
                "description": generated_description_response,
                "time_taken_images": total_processing_time_images,
                "time_taken_text_generation": total_processing_time_textGeneration
                
            }
        }
    except Exception as e:
        print(e, "error")
        return CustomErrorResponse.generate_response("Error", str(e), 500)


             
