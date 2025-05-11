from fastapi import FastAPI, Form, File, UploadFile, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from datetime import datetime
import cloudinary
import cloudinary.uploader
import os
from fastapi import Request
import uvicorn
import json
# from config import settings

# Initialize FastAPI app
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)



# Cloudinary configuration
cloudinary.config(
    cloud_name='dsh0zdhrt',
    api_key='586173347811638',
    api_secret='_75ftja3Iclwb_LJ7nWwNPQM6aE',
)

# cloudinary.config(
#     cloud_name=settings.cloudinary_cloud_name,
#     api_key=settings.cloudinary_api_key,
#     api_secret=settings.cloudinary_api_secret,
# )


# OAuth2 scheme for authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Database connection configuration
DATABASE_URL = "postgresql://postgres:1432@localhost/postgres"
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)


# Example Property model
class Property(BaseModel):
    id: int
    title: str
    description: str
    price: str
    image: List[str]
    location: str
    configuration:str
    area:str
    property_age:str
    furnishing:str



class User(BaseModel):
    username: str
    password: str
    created_at:str

class Contact(BaseModel):
    name: str
    email: str
    phone: str
    message: str
    # send_at:str

class inquiry(BaseModel):
    property_id:int
    property_title:str
    name: str
    email: str
    phone: str
    message: str
    # send_at:str

# Authentication check
def get_current_user(token: str = Depends(oauth2_scheme)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE password = %s", (token,))
    user = cursor.fetchone()
    conn.close()
    if user:
        return {"username": user[0]}
    raise HTTPException(status_code=401, detail="Invalid authentication credentials")

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT password FROM users WHERE username = %s", (form_data.username,)
    )
    user = cursor.fetchone()
    conn.close()
    if user and user[0] == form_data.password:
        return {"access_token": form_data.password, "token_type": "bearer"}
    raise HTTPException(status_code=400, detail="Invalid username or password")

@app.post("/register")
async def register(user: User):
    conn = get_db_connection()
    cursor = conn.cursor()
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # print('current_datetime',current_datetime)
    try:
        cursor.execute(
            "INSERT INTO users (username, password,create_at) VALUES (%s, %s,%s)",
            (user.username, user.password,current_datetime)
        )
        conn.commit()
    except psycopg2.Error as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail="Error registering user: " + str(e))
    finally:
        conn.close()
    return {"message": "User registered successfully"}


@app.get("/properties", response_model=List[Property])
async def get_properties(search: Optional[str] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM properties"
    params = ()

    if search:
        query += " WHERE title ILIKE %s OR description ILIKE %s OR location ILIKE %s"  
        params = (f"%{search}%", f"%{search}%", f"%{search}%")

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    # Process each row from the database and convert image URLs into a list
    properties = [
        Property(
            id=row[0],
            title=row[1],
            description=row[2],
            price=row[3],
            image=[row[4]] if row[4] else [],  # Ensure image is wrapped in a list
            location=row[5],
            create_at=row[6],
            configuration=row[7],
            area=row[8],
            property_age=row[9],
            furnishing=row[10]
        )
        for row in rows
    ]

    return properties



@app.get("/properties/{property_id}", response_model=Property)
async def get_property_by_id(property_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM properties WHERE id = %s", (property_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        property = Property(
            id=row[0],
            title=row[1],
            description=row[2],
            price=row[3],
            image=[row[4]] if row[4] else [],
            location=row[5],
            create_at=row[6],
            configuration=row[7],
            area=row[8],
            property_age=row[9],
            furnishing=row[10]

        )
        return property
    else:
        raise HTTPException(status_code=404, detail="Property not found")


@app.get("/inquiries/{property_id}", response_model=List[inquiry])
async def get_inquiries_by_id(property_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inquiries WHERE property_id = %s", (property_id,))
    row = cursor.fetchall()
    conn.close()

    if row:
        inquiries =[ inquiry(
            id=row[0],
            property_id=row[1],
            property_title=row[2],
            name=row[3],
            email=row[4],
            phone=row[5],
            message=row[6],
            send_at=row[7]
        )
        for row in row
        ]
        return inquiries
    else:
        raise HTTPException(status_code=404, detail="inquiries not found")


@app.post("/properties", response_model=Property, dependencies=[Depends(get_current_user)])
async def add_property(
    title: str = Form(...),
    description: str = Form(...),
    price: str = Form(...),
    location: str = Form(...),
    images: List[UploadFile] = File(...),  # Accept multiple images
    configuration:str=Form(...),
    area:str=Form(...),
    property_age:str=Form(...),
    furnishing:str=Form(...)
):
    # Log the received data
    print(f"Received property data: title={title}, description={description}, price={price}, location={location},configuration={configuration},area={area},property_age={property_age},furnishing={furnishing}")
    print(f"Received images: {[image.filename for image in images]}")
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # print('current_datetime',current_datetime)

    try:
        image_urls = []
        # Upload each image to Cloudinary and store the URL
        for image in images:
            upload_result = cloudinary.uploader.upload(image.file)
            image_url = upload_result.get("url")
            image_urls.append(image_url)
            print(f"Uploaded image URL: {image_url}")

        # Insert property into the database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO properties (title, description, price, image, location,configuration,area,property_age,furnishing,created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
            # "INSERT INTO properties (title, description, price, image, location) VALUES (%s, %s, %s, %s, %s) RETURNING id",

            (title, description, price, image_urls, location,configuration,area,property_age,furnishing,current_datetime)
        )
        property_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()

        # Create and return the property object
        property = Property(
            id=property_id,
            title=title,
            description=description,
            price=price,
            image=image_urls,
            location=location,
            configuration=configuration,
            area=area,
            property_age=property_age,
            furnishing=furnishing
        )
        return property

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=422, detail=f"Error: {str(e)}")

@app.post("/contact")
async def store_contact(contact: Contact):
    conn = get_db_connection()
    cursor = conn.cursor()
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    
    try:
        # Insert contact information into the 'contact' table
        cursor.execute(
            """
            INSERT INTO contact (name, email, phone, message,send_at)
            VALUES (%s, %s, %s, %s, %s) RETURNING id
            """, 
            (contact.name, contact.email, contact.phone, contact.message,current_datetime)
        )
        contact_id = cursor.fetchone()[0]  # Retrieve the ID of the newly inserted contact
        conn.commit()
        
        return {"message": "Contact information saved successfully!", "contact_id": contact_id}
    
    except psycopg2.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save contact information: {e}")
    
    finally:
        conn.close()

@app.post("/inquiry")
async def store_inquiry(inquiry: inquiry):  # You can define a model for this as well
    conn = get_db_connection()
    cursor = conn.cursor()
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    
    try:
        # Insert contact information into the 'contact' table
        cursor.execute(
            """
            INSERT INTO inquiries (property_id,property_title,name, email, phone, message,send_at)
            VALUES (%s, %s,%s, %s, %s, %s, %s) RETURNING id
            """, 
            (inquiry.property_id,inquiry.property_title,inquiry.name, inquiry.email, inquiry.phone, inquiry.message,current_datetime)
        )
        inquiry_id = cursor.fetchone()[0]  # Retrieve the ID of the newly inserted contact
        conn.commit()
        
        return {"message": "information saved successfully!", "inquiry_id": inquiry_id}
    
    except psycopg2.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save contact information: {e}")
    
    finally:
        conn.close()


@app.put("/properties/{property_id}", response_model=Property, dependencies=[Depends(get_current_user)])
async def update_property(
    property_id: int,
    title: str = Form(...),
    description: str = Form(...),
    price: str = Form(...),
    location: str = Form(...),
    configuration: str = Form(...),
    area: str = Form(...),
    property_age: str = Form(...),
    furnishing: str = Form(...),
    images: Optional[List[UploadFile]] = File(None)
):
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch existing images if no new ones provided
        cursor.execute("SELECT image FROM properties WHERE id = %s", (property_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Property not found")

        try:
            existing_images = json.loads(row[0]) if row[0] else []
        except json.JSONDecodeError:
            # fallback in case it's in {url} format or bad string
            existing_images = row[0].strip('{}').split(',') if row[0] else []
            
        # Upload new images if provided
        if images:
            image_urls = []
            for image in images:
                upload_result = cloudinary.uploader.upload(image.file)
                image_url = upload_result.get("url")
                image_urls.append(image_url)
        else:
            image_urls = existing_images  # reuse old ones

        # Convert image_urls to a string (JSON serialization)
        image_urls_str = json.dumps(image_urls)

        # Update query
        cursor.execute("""
            UPDATE properties 
            SET title = %s, description = %s, price = %s, image = %s, location = %s,
                configuration = %s, area = %s, property_age = %s, furnishing = %s,
                update_at = %s
            WHERE id = %s
        """, (
            title, description, price, image_urls_str, location,
            configuration, area, property_age, furnishing,
            current_datetime, property_id
        ))

        conn.commit()
        conn.close()

        # Return updated property data
        return Property(
            id=property_id,
            title=title,
            description=description,
            price=price,
            image=image_urls,  # Send back the original list, not the string
            location=location,
            configuration=configuration,
            area=area,
            property_age=property_age,
            furnishing=furnishing
        )

    except Exception as e:
        print(f"Update error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update property: {str(e)}")

@app.delete("/properties/{property_id}", dependencies=[Depends(get_current_user)])
async def delete_property(property_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM properties WHERE id = %s", (property_id,))
    conn.commit()
    conn.close()
    return {"message": "Property deleted successfully"}


@app.get("/user", dependencies=[Depends(get_current_user)])
def get_user(token: str = Depends(oauth2_scheme)):
    user = get_current_user(token)
    return user


if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)
    