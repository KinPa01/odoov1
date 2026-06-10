import xmlrpc.client

url = 'http://localhost:8044'
try:
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    dbs = common.list()
    print("Databases:", dbs)
except Exception as e:
    print("Error:", e)
