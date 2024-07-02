from fastapi import APIRouter, UploadFile, File, Form
from app.services.content_generation_service import generate_img_desc, generate_openai_content, generate_mixtral_content, remove_s_tag, cache_client, generate_anthropic_content
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

@router.post("/product-content-generator/anthropic/threading")
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
        

        def process_file(file,filename):
            cached_data = cache_client.get(filename)
            if cached_data:
                text, desc = cached_data
                text_objects_images_ocr_values.append(text)
                objects_descriptions.append(desc)
            else:
                print('no cached data found')
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

                cache_client[filename] = (text_objects_images_ocr_values[-1], objects_descriptions[-1])

 
        async def process_files(files):
            threads = []
            for file in files:
                if file.filename == "":
                    return CustomErrorResponse.generate_response("Invalid Input", "File name cannot be empty", 400)
                
                content = await file.read()
                thread = threading.Thread(target=process_file, args=(content,file.filename))
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
            product_prompt=f'Give a product title of in exact {str(title_word_limit)} words and product description in {str(description_word_limit)} in {language} language within a JSON object..'
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

            generated_response = generate_anthropic_content(product_prompt)
            
            print(generated_response)
            # generated_title_response = generated_response['product_title']
            # generated_description_response = generated_response['product_description']
            # feature_points = generated_response['feature_points']
            # numbered_feature_points = [f"{i+1}. {point}" for i, point in enumerate(feature_points)]
            # generated_description_response = generated_description_response + '\n\nFeature Points:\n' + '\n'.join(numbered_feature_points)
    
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
            generated_response = generate_anthropic_content(product_prompt)
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
            generated_response = generate_anthropic_content(product_prompt)
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



 # if title=='true' and description=='true':
        #     product_prompt=f'Give a product title of above {str(title_word_limit)} words and product description in {str(description_word_limit)} in {language} language.'
        #     if category:
        #         print(category,'sc')
        #         product_prompt += f", the product is of specific category : {category}"
        #     if product_context:
        #         product_prompt += f",with the context of the product is: {product_context}"
        #     if objects_images_string:
        #         product_prompt += f", where the visuals of the product are: {objects_images_string}"
        #     if text_objects_images_ocr_string:
        #         product_prompt += f", some more detailed information about the product is: {text_objects_images_ocr_string}"
        #         if category=='Electronics':
        #             product_prompt+='add specifications if exists in feature_points'
        #         elif category=='Food':
        #             product_prompt+='add all Nutrition Facts that exists, in feature_points'

        #     product_prompt += f" product title must be above {str(title_word_limit)} words and product description must be in {str(description_word_limit)} words "
            
        #     format='{"title":"generated_title","description":"generated_description","feature_points":["generated_feature_point_1","generated_feature_point_2","generated_feature_point_3",...]}'
        #     product_prompt += f" in this json format:{format}"
        #     generated_response = generate_openai_content(product_prompt)
        #     generated_title_response = generated_response['title']
        #     generated_description_response = generated_response['description']
        #     feature_points = generated_response['feature_points']
        #     numbered_feature_points = [f"{i+1}. {point}" for i, point in enumerate(feature_points)]
        #     generated_description_response = generated_description_response + '\n\nFeature Points:\n' + '\n'.join(numbered_feature_points)
          
       
# @router.post("/product-content-generator/openai/threading")
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
        
#         text_objects_images_ocr_string = ""
#         objects_images_string = ""
#         objects_descriptions = []
#         text_objects_images_ocr_values = []
#         total_processing_time_textGeneration = 0
#         total_processing_time_images=0
#         generated_title_response=''
#         generated_description_response=''
        

#         def process_file(file,filename):
#             cached_data = cache_client.get(filename)
#             if cached_data:
#                 text, desc = cached_data
#                 text_objects_images_ocr_values.append(text)
#                 objects_descriptions.append(desc)
#             else:
#                 print('no cached data found')
#                 img = Image.open(BytesIO(file)).convert("RGB")

#                 def ocr_and_append(img):
#                     text = pytesseract.image_to_string(img)
#                     text_objects_images_ocr_values.append(text)

#                 def generate_desc_and_append(img):
#                     image_description = generate_img_desc(img)
#                     objects_descriptions.append(image_description)

#                 thread_ocr = threading.Thread(target=ocr_and_append, args=(img,))
#                 thread_desc = threading.Thread(target=generate_desc_and_append, args=(img,))
#                 thread_ocr.start()
#                 thread_desc.start()
#                 thread_ocr.join()
#                 thread_desc.join()

#                 cache_client[filename] = (text_objects_images_ocr_values[-1], objects_descriptions[-1])

 
#         async def process_files(files):
#             threads = []
#             for file in files:
#                 if file.filename == "":
#                     return CustomErrorResponse.generate_response("Invalid Input", "File name cannot be empty", 400)
                
#                 content = await file.read()
#                 thread = threading.Thread(target=process_file, args=(content,file.filename))
#                 thread.start()
#                 threads.append(thread)
            
#             for thread in threads:
#                 thread.join()
        
#         start_time = time.time()
#         if files:
#             await process_files(files)
          
#         end_time = time.time()
#         total_processing_time_images = end_time - start_time

#         text_objects_images_ocr_string = ', '.join(text_objects_images_ocr_values)
#         objects_images_string = ', '.join(objects_descriptions)
        
#         start_time = time.time()
        
#         if title=='true' and description=='true':
#             product_prompt=f'Give a product title of above {str(title_word_limit)} words and product description in {str(description_word_limit)} in {language} language.'
#             if category:
#                 print(category,'sc')
#                 product_prompt += f", the product is of specific category : {category}"
#             if product_context:
#                 product_prompt += f",with the context of the product is: {product_context}"
#             if objects_images_string:
#                 product_prompt += f", where the visuals of the product are: {objects_images_string}"
#             if text_objects_images_ocr_string:
#                 product_prompt += f", some more detailed information about the product is: {text_objects_images_ocr_string}"
#                 if category=='Electronics':
#                     product_prompt+='add specifications if exists in feature_points'
#                 elif category=='Food':
#                     product_prompt+='add all Nutrition Facts that exists, in feature_points'

#             product_prompt += f" product title must be above {str(title_word_limit)} words and product description must be in {str(description_word_limit)} words "
            
#             format='{"title":"generated_title","description":"generated_description","feature_points":["generated_feature_point_1","generated_feature_point_2","generated_feature_point_3",...]}'
#             product_prompt += f" in this json format:{format}"
#             generated_response = generate_openai_content(product_prompt)
#             generated_title_response = generated_response['title']
#             generated_description_response = generated_response['description']
#             feature_points = generated_response['feature_points']
#             numbered_feature_points = [f"{i+1}. {point}" for i, point in enumerate(feature_points)]
#             generated_description_response = generated_description_response + '\n\nFeature Points:\n' + '\n'.join(numbered_feature_points)
    
#         elif title=='true':
#             product_prompt=f'Give a product title in around {str(title_word_limit)} words in {language} language.'
#             if category:
#                 product_prompt += f", the product is of {category} category. "
#             if product_context:
#                 product_prompt += f",with the context of the product is: {product_context}"
#             if objects_images_string:
#                 product_prompt += f", where the visuals of the product are: {objects_images_string}"
#             if text_objects_images_ocr_string:
#                 product_prompt += f", some more detailed information about the product is: {text_objects_images_ocr_string}"
                
#             product_prompt += f" product title must be above in around {str(title_word_limit)} words "
#             format='{"title":"generated_title"}'
#             product_prompt += f" in this json format:{format}"
#             generated_response = generate_openai_content(product_prompt)
#             generated_title_response = generated_response['title']
             
#         elif description=='true':
#             product_prompt=f'Give a product description in {language} language.'
#             if category:
#                 product_prompt += f", the product is of specific category : {category}"
#             if product_context:
#                 product_prompt += f",with the context of the product is: {product_context}"
#             if objects_images_string:
#                 product_prompt += f", where the visuals of the product are: {objects_images_string}"
#             if text_objects_images_ocr_string:
#                 product_prompt += f", some more detailed information about the product is: {text_objects_images_ocr_string}"
                
#             product_prompt += f" give description in around {str(description_word_limit)} words"
#             format='{"description":"generated_description","feature_points":["generated_feature_point_1","generated_feature_point_2","generated_feature_point_3",...]}'
#             product_prompt += f" in this json format:{format}" 
#             generated_response = generate_openai_content(product_prompt)
#             generated_description_response = generated_response['description']
#             feature_points = generated_response['feature_points']
#             numbered_feature_points = [f"{i+1}. {point}" for i, point in enumerate(feature_points)]
#             generated_description_response = generated_description_response + '\n\nFeature Points:\n' + '\n'.join(numbered_feature_points)
            
#         end_time = time.time()
#         total_processing_time_textGeneration = end_time - start_time
         
#         return {
#             "status": ResponseValues.SUCCESS,
#             "message": "Generated successfully",
#             "body": {
#                 "title": generated_title_response,
#                 "description": generated_description_response,
#                 "time_taken_images": total_processing_time_images,
#                 "time_taken_text_generation": total_processing_time_textGeneration
                
#             }
#         }
#     except Exception as e:
#         print(e, "error")
#         return CustomErrorResponse.generate_response("Error", str(e), 500)

@router.post("/product-content-generator/openai/threading")
async def product_desc(files: List[UploadFile] = File(None), 
                     title_word_limit: str = Form('40'),
                     description_word_limit: str = Form('100'),
                     title: str = Form('false'),
                     description: str = Form('false'),
                     category: str = Form(None),
                     brand: str = Form(None),
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
        
        def process_file(file,filename):
            cached_data = cache_client.get(filename)
            if cached_data:
                text, desc = cached_data
                text_objects_images_ocr_values.append(text)
                objects_descriptions.append(desc)
            else:
                print('no cached data found')
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

                cache_client[filename] = (text_objects_images_ocr_values[-1], objects_descriptions[-1])

        async def process_files(files):
            threads = []
            for file in files:
                if file.filename == "":
                    return CustomErrorResponse.generate_response("Invalid Input", "File name cannot be empty", 400)
                
                content = await file.read()
                thread = threading.Thread(target=process_file, args=(content,file.filename))
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
        
        repsonse_obj=generate_openai_content(f'from these inputs:{objects_images_string} identify the one main product without brand name just the product.')
       
        if title=='true':
            product_prompt=f'Give a product title in above {str(title_word_limit)} words in {language} language.'
            if brand:
                product_prompt += f", the product brand name is: {brand}  "
            if category:
                product_prompt += f", the product is of {category} category. "
            if product_context:
                product_prompt += f",with the context of the product is: {product_context}"
            if repsonse_obj:
                product_prompt += f",where the product is: : {repsonse_obj}"
            if text_objects_images_ocr_string:
                product_prompt += f", some details of product is: {text_objects_images_ocr_string}"
                
            product_prompt += f" product title must be above in above {str(title_word_limit)} words "
            format='{"title":"generated_title"}'
            product_prompt += f" in this json format:{format}"
            generated_response = generate_openai_content(product_prompt)
            generated_title_response = generated_response['title']
             
        if description=='true':
            product_prompt=f'Give a product description in {language} language.'
            if brand:
                product_prompt += f", the product brand name is: {brand}  "
            if category:
                product_prompt += f", the product is of specific category : {category}"
            if product_context:
                product_prompt += f",with the context of the product is: {product_context}"
            if repsonse_obj:
                product_prompt += f", where the product is: {repsonse_obj}"
            if text_objects_images_ocr_string:
                product_prompt += f", some more detailed information about the product is: {text_objects_images_ocr_string}"
                
            product_prompt += f" give description in around {str(description_word_limit)} words"
            format='{"description":"generated_description","feature_points":["generated_feature_point_1","generated_feature_point_2","generated_feature_point_3",...]}'
            product_prompt += f" in this json format:{format}" 
            generated_response = generate_openai_content(product_prompt)
            generated_description_response = generated_response['description']
            feature_points = generated_response['feature_points']
            numbered_feature_points = [f"{i+1}. {point}" for i, point in enumerate(feature_points)]
            generated_description_response = generated_description_response + '\n\n' + '\n'.join(numbered_feature_points)
            
        end_time = time.time()
        total_processing_time_textGeneration = end_time - start_time
         
        return {
            "status": ResponseValues.SUCCESS,
            "message": "Generated successfully",
            "body": {
                "title": generated_title_response,
                "description": generated_description_response,
                "time_taken_images": total_processing_time_images,
                "time_taken_text_generation": total_processing_time_textGeneration,
                "language": language
                
            }
        }
    except Exception as e:
        print(e, "error")
        return CustomErrorResponse.generate_response("Error", str(e), 500)

@router.post("/product-content-generator/openai/translate")
async def product_desc(
                    language: str = Form('English'),
                    description: str = Form(None),
                    title: str = Form(None)):
    try:
       
        
        if title == '' and description == '':
            return CustomErrorResponse.generate_response("Invalid Input", "Title/Description one should be there", 400)
        if language == '' :
            return CustomErrorResponse.generate_response("Invalid Input", "Give Language input", 400)
        generated_title_response=''
        generated_description_response=''
        
      
        if title!=None:
            product_prompt=f'convert this product title: {title} to {language} language'     
            format='{"title":"generated_title"}'
            product_prompt += f" in this json format:{format}"
            generated_response = generate_openai_content(product_prompt)
            print(generated_response)
            generated_title_response = generated_response['title']
            print("generated_title_response",generated_title_response)
            
             
        if description!=None :
            product_prompt=f'convert to {language} language . this the text: {description} '     

            format='{"description":"generated_description","feature_points":["generated_feature_point_1","generated_feature_point_2","generated_feature_point_3",...]}'
            product_prompt += f" in this json format:{format}" 
            print(product_prompt)
            generated_response = generate_openai_content(product_prompt)
            print(generated_response)
            generated_description_response = generated_response['description']
            feature_points = generated_response['feature_points']
            numbered_feature_points = [f"{i+1}. {point}" for i, point in enumerate(feature_points)]
            generated_description_response = generated_description_response + '\n\n' + '\n'.join(numbered_feature_points)
            

         
        return {
            "status": ResponseValues.SUCCESS,
            "message": "translated successfully",
            "body": {
                "title": generated_title_response,
                "description": generated_description_response,
                "language": language
                
            }
        }
    except Exception as e:
        print(e, "error")
        return CustomErrorResponse.generate_response("Error", str(e), 500)

@router.post("/product-content-generator/openai/gen-seo")
async def product_desc(description: str = Form(None),language: str = Form('English')):
    try:
       
        
        if language == '' and description == '':
            return CustomErrorResponse.generate_response("Invalid Input", "Description one should be there", 400)
        
        
        
        if description!=None:
            format='{"title_tag":"generated_title_tag", "meta_description":"generated_meta_description_tag", "keywords":"generated_keyword","header":"generated_header_tags"}'
            
            product_prompt=f'give me seo tags based on this product descripiton:{description} in this format:{format}'     
            
            generated_response = generate_openai_content(product_prompt)
           
            
             
     

         
        return {
            "status": ResponseValues.SUCCESS,
            "message": "translated successfully",
            "body": {
                "seodata": generated_response,
                "language": language
            }
        }
    except Exception as e:
        print(e, "error")
        return CustomErrorResponse.generate_response("Error", str(e), 500)




