import string
import random
import pickle

uuid_path = 'testing/uuids.pkl'
with open(uuid_path, 'rb') as file:
    uuids = pickle.load(file)

def uuid_generator(length=4):
    characters = string.ascii_letters + string.digits
    while True:
        u = ''.join(random.choices(characters, k=length))
        if u in uuids:
            continue
        uuids.add(u)
        with open(uuid_path, 'wb') as file:
            pickle.dump(uuids, file)
        return u

if __name__=='__main__':
    print(uuid_generator())