from time import time
import json
import hashlib
from uuid import uuid4
import sys
from flask import Flask, jsonify, request
from urllib.parse import urlparse
import requests

# ardalan.dsht@gmail.com
# noronmind@protonmail.com

# This blockchain is for educational purposes only.
# The chain is a python list and the blocks are stored as json.
# The transactions are stored as json too.
# Mining reward is 100 Noron Coins.
# Blocks are stored on system RAM, so be careful.
# Only nodes are able to send and receive Noron Coins,there are no secret keys.
# The genesis block is made wright after running the code, the nodes will get the valid chain afterwards.


class Blockchain:
    def __init__(self):
        self.chain = []
        self.mem_pool = []
        self.new_block(previous_hash=1, proof=100)  # This is the genesis block.
        self.nodes = set()  # We use sets instead of lists for not registering repeated nodes.

    def new_block(self, proof, previous_hash=None):
        # If there isn't "previous_hash" in input use "None" otherwise use the input.
        # previous_hash=None is only used for the genesis block cause the chain list is empty.
        block = {
            "index": len(self.chain) + 1,
            "timestamp": time(),
            "transactions": self.mem_pool,
            "proof": proof,
            "previous_hash": previous_hash or self.hash(self.chain[-1])
        }
        self.mem_pool = []  # For emptying the Memory pool.
        self.chain.append(block)  # Add block to the end of the chain.
        return block

    def new_trx(self, sender, recipient, amount):
        # Add new transaction to the Memory pool.
        self.mem_pool.append({
            "sender": sender,
            "recipient": recipient,
            "amount": amount
        })
        return self.last_block["index"] + 1  # This is the index of the next block.

    @staticmethod
    def hash(block):
        # It hashes the given block.
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def register_node(self, address):
        # This adds a new node to the network.
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def valid_chain(self, chain):
        # Checks if a chain is valid or not.
        # Its used for resolving conflicts.
        last_block = chain[0]
        current_index = 1
        while current_index < len(chain):
            block = chain[current_index]
            if block["previous_hash"] != self.hash(last_block):
                return False
            if not self.valid_proof(last_block["proof"], block["proof"]):
                return False
            last_block = block
            current_index = current_index + 1
        return True

    def resolve_conflicts(self):
        # Checks all nodes and selects the best chain in the network.
        neighbours = self.nodes
        new_chain = None
        max_length = len(self.chain)
        for node in neighbours:
            response = requests.get(f"http://{node}/chain")
            if response.status_code == 200:
                length = response.json()["length"]
                chain = response.json()["chain"]
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain
        if new_chain:
            self.chain = new_chain
            return True
        else:
            return False

    @property
    def last_block(self):
        # Returns last block as an object,because of property decorator.
        return self.chain[-1]

    @staticmethod
    def valid_proof(last_proof, proof):
        # This method only works with "proof_of_work" method.
        # Its used for guessing hashes for the proof of work.
        guess = f' {proof}{last_proof} '.encode()  # Encode makes the object like a string.
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

    def proof_of_work(self, last_proof):
        proof = 0  # Zero is the first number in "valid_proof"s loop which tries to fiend the correct hash.
        while self.valid_proof(last_proof, proof) is False:
            proof = proof + 1
        return proof


app = Flask(__name__)


@app.route("/mine")
def mine():
    # This method mines a new block and adds to the chain.
    last_block = blockchain.last_block
    last_proof = last_block["proof"]
    proof = blockchain.proof_of_work(last_proof)
    blockchain.new_trx(sender="0", recipient=node_id, amount=100)  # The mining reward is 100 coins.
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)
    response = {
        "message": "new block created",
        "index": block["index"],
        "transactions": block["transactions"],
        "proof": block["proof"],
        "previous_hash": block["previous_hash"]
    }
    return jsonify(response), 200


@app.route("/transactions/new", methods=["POST"])
def new_trx():  # This will add a new transaction.
    values = request.get_json()
    this_block = blockchain.new_trx(values["sender"], values["recipient"], values["amount"])
    response = {"message": f"will be added to block{this_block}"}
    return jsonify(response), 201


@app.route("/chain")
def full_chain():
    # Shows the entire chain.
    response = {
        "chain": blockchain.chain,
        "length": len(blockchain.chain)
    }
    return jsonify(response), 200


@app.route("/nodes/register", methods=["POST"])
def register_node():
    # This is for adding a list of nodes to the nodes set.
    # exp: {"nodes" : ["http://localhost:6000"]}
    values = request.get_json()
    nodes = values.get("nodes")
    for node in nodes:
        blockchain.register_node(node)
    response = {
        "message": "nodes added",
        "total_nodes": list(blockchain.nodes)
    }
    return jsonify(response), 201


@app.route("/nodes/resolve")
def consensus():
    # This is for merging two node chains into one chain.
    replaced = blockchain.resolve_conflicts()
    if replaced:
        response = {
            "message": "replaced!",
            "new_chain": "blockchain.chain",
        }
    else:
        response = {
            "message": "Im the best",
            "chain": blockchain.chain
        }
    return jsonify(response), 200


node_id = str(uuid4())  # It makes a four part string.
blockchain = Blockchain()
if __name__ == "__main__":
    # It allows us to run the app on different ports.
    app.run(host="0.0.0.0", port=sys.argv[1])
