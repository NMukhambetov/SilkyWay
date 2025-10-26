from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import backend.queries as queries

app = FastAPI(title="SilkyWay Product API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/products")
def list_products():
    return queries.get_all_products()

@app.get("/products/{product_id}")
def get_product(product_id: int):
    product = queries.get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.post("/products")
def create_product(data: dict):
    try:
        product_id = queries.add_product(data["name"], data["description"], data["price"], data["stock"])
        return {"message": "Product added successfully", "id": product_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/products/{product_id}")
def update_product(product_id: int, data: dict):
    updated = queries.update_product(product_id, data["name"], data["description"], data["price"], data["stock"])
    if not updated:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product updated successfully"}

@app.delete("/products/{product_id}")
def delete_product(product_id: int):
    deleted = queries.delete_product(product_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted successfully"}

@app.get("/search/{keyword}")
def search(keyword: str):
    return queries.search_products(keyword)

@app.get("/lowstock")
def low_stock(threshold: int = 5):
    return queries.get_low_stock(threshold)
