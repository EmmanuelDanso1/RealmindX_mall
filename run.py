from waitress import serve
from e_commerce import create_app

app = create_app()

if __name__ == '__main__':
    print("Starting server at http://127.0.0.1:5001 ...")
    serve(app, host='127.0.0.1',  port=5001)
