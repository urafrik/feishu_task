try:
    import larksuite as lark
    print("Successfully imported 'larksuite as lark'")
    print(lark.__version__)
except ImportError:
    print("Failed to import 'larksuite'")

try:
    import lark_oapi as lark
    print("Successfully imported 'lark_oapi as lark'")
    print(lark.__version__)
except ImportError:
    print("Failed to import 'lark_oapi'") 