from pymongo import MongoClient
import os

MONGO_URI = "mongodb://rashadbayramov815:Rashad1994@62.72.22.62:27017/?authSource=admin"
DB_NAME = "agent_swarm_os"

def purge():
    print(f"Connecting to {MONGO_URI}...")
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    try:
        # Check connection
        client.admin.command('ping')
        print("Ping successful.")
        
        db = client[DB_NAME]
        collections = db.list_collection_names()
        print(f"Collections to purge: {collections}")
        
        for coll in collections:
            print(f"Dropping collection: {coll}")
            db.drop_collection(coll)
            
        print("✅ Database cleared.")
    except Exception as e:
        print(f"❌ Failed to purge database: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    purge()
