from tempfile import NamedTemporaryFile

from flask import Flask, abort, request, jsonify, send_file

app = Flask(__name__)

cur_id: int = 0
products = []
images = {}
@app.route('/product', methods=['POST'])
def add_new_product():
    global cur_id
    if not request.json or 'name' not in request.json or 'description' not in request.json:
        abort(400)

    new_product = {
        'id': cur_id,
        'name': request.json["name"],
        'description': request.json["description"],
        'filename': ''
    }
    cur_id += 1
    products.append(new_product)
    return jsonify(new_product), 201

@app.route("/product/<int:product_id>", methods=["GET"])
def get_product(product_id):
    product = list(filter(lambda cur_product: cur_product['id'] == product_id, products))
    if len(product) == 0:
        abort(404)
    return jsonify(product[0])

@app.route("/product/<int:product_id>", methods=["PUT"])
def update_product(product_id):
    if not request.json:
        abort(400)

    product = list(filter(lambda cur_product: cur_product['id'] == product_id, products))
    if len(product) == 0:
        abort(404)
    if len(request.json) > 2 or ('name' not in request.json and 'description' not in request.json):
        abort(400)

    product[0]['name'] = request.json.get('name', product[0]['name'])
    product[0]['description'] = request.json.get('description', product[0]['description'])

    return jsonify(product[0])
@app.route("/product/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):
    product = list(filter(lambda cur_product: cur_product['id'] == product_id, products))
    if len(product) == 0:
        abort(404)
    products.remove(product[0])
    images.pop(product_id, None)
    return jsonify(product[0])

@app.route("/products", methods=["GET"])
def get_products():
    return jsonify(products)

@app.route("/product/<int:product_id>/image", methods=["POST"])
def add_icon(product_id):
    product = list(filter(lambda cur_product: cur_product['id'] == product_id, products))
    if len(product) == 0:
        abort(404)
    product[0]['filename'] = request.files['icon'].filename
    saved_image = NamedTemporaryFile()
    request.files['icon'].save(saved_image.name)
    images[product_id] = saved_image
    return jsonify(product[0])

@app.route("/product/<int:product_id>/image", methods=["GET"])
def get_icon(product_id):
    if product_id not in images:
        abort(404)
    product = list(filter(lambda cur_product: cur_product['id'] == product_id, products))
    return send_file(images[product_id], download_name=product[0]['filename'])

if __name__ == '__main__':
    app.run()
