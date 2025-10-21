from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import queries

app = FastAPI()

class Product(BaseModel):
    name: str
    description: str
    price: float
    stock: int

@app.get("/products")
def get_products():
    try:
        return queries.get_all_products()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/products/{product_id}")
def get_product(product_id: int):
    try:
        product = queries.get_product_by_id(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/products")
def add_product(product: Product):
    try:
        queries.add_product(product.name, product.description, product.price, product.stock)
        return {"message": "Product added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/products/{product_id}")
def update_product(product_id: int, product: Product):
    try:
        queries.update_product(product_id, product.name, product.description, product.price, product.stock)
        return {"message": "Product updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/products/{product_id}")
def delete_product(product_id: int):
    try:
        queries.delete_product(product_id)
        return {"message": "Product deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
