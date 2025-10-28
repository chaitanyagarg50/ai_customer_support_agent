import streamlit as st
import google.generativeai as genai
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# Set up the Streamlit App
st.title("AI Customer Support Agent with Memory 🛒")
st.caption("Chat with a customer support assistant who remembers your past interactions.")

# Hardcode the Gemini API key (replace with your actual key)
GEMINI_API_KEY = "AIzaSyBpDskmsD5cOk8qA_xjT3Arv8cnEi_Vug4"  # Replace with your valid Gemini API key

# Configure the Gemini API
os.environ['GOOGLE_API_KEY'] = GEMINI_API_KEY
genai.configure(api_key=GEMINI_API_KEY)

# Custom in-memory storage
class InMemoryStorage:
    def __init__(self):
        self.memories = {}  # Dictionary to store memories by user_id

    def add(self, content: str, user_id: Optional[str] = None, metadata: Optional[Dict] = None):
        """Add a memory for a user."""
        if user_id not in self.memories:
            self.memories[user_id] = []
        self.memories[user_id].append({
            "memory": content,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        })

    def search(self, query: str, user_id: Optional[str] = None) -> Dict:
        """Search memories for a user (simple keyword match)."""
        if user_id not in self.memories:
            return {"results": []}
        # Basic search: return memories containing the query string
        results = [
            mem for mem in self.memories[user_id]
            if query.lower() in mem["memory"].lower()
        ]
        return {"results": results}

    def get_all(self, user_id: Optional[str] = None) -> Dict:
        """Retrieve all memories for a user."""
        if user_id not in self.memories:
            return {"results": []}
        return {"results": self.memories[user_id]}

class CustomerSupportAIAgent:
    def __init__(self):
        # Initialize in-memory storage
        self.memory = InMemoryStorage()
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.app_id = "customer-support"

    def handle_query(self, query, user_id=None):
        try:
            # Search for relevant memories
            relevant_memories = self.memory.search(query=query, user_id=user_id)
            
            # Build context from relevant memories
            context = "Relevant past information:\n"
            if relevant_memories and "results" in relevant_memories:
                for memory in relevant_memories["results"]:
                    if "memory" in memory:
                        context += f"- {memory['memory']}\n"

            # Generate a response using Gemini
            full_prompt = f"""You are a customer support AI agent for TechGadgets.com, an online electronics store.
{context}
Customer: {query}
Support Agent:"""
            response = self.model.generate_content(full_prompt)
            answer = response.text

            # Add the query and answer to memory
            self.memory.add(query, user_id=user_id, metadata={"app_id": self.app_id, "role": "user"})
            self.memory.add(answer, user_id=user_id, metadata={"app_id": self.app_id, "role": "assistant"})

            return answer
        except Exception as e:
            st.error(f"An error occurred while handling the query: {e}")
            return "Sorry, I encountered an error. Please try again later."

    def get_memories(self, user_id=None):
        try:
            # Retrieve all memories for a user
            return self.memory.get_all(user_id=user_id)
        except Exception as e:
            st.error(f"Failed to retrieve memories: {e}")
            return None

    def generate_synthetic_data(self, user_id: str) -> dict | None:
        try:
            today = datetime.now()
            order_date = (today - timedelta(days=10)).strftime("%B %d, %Y")
            expected_delivery = (today + timedelta(days=2)).strftime("%B %d, %Y")

            prompt = f"""You are a data generation AI that creates realistic customer profiles and order histories. Generate a detailed customer profile and order history for a TechGadgets.com customer with ID {user_id}. Include:
            1. Customer name and basic info
            2. A recent order of a high-end electronic device (placed on {order_date}, to be delivered by {expected_delivery})
            3. Order details (product, price, order number)
            4. Customer's shipping address
            5. 2-3 previous orders from the past year
            6. 2-3 customer service interactions related to these orders
            7. Any preferences or patterns in their shopping behavior

            Format the output as a valid JSON object."""

            response = self.model.generate_content(prompt)
            customer_data = json.loads(response.text.strip('```json\n').strip('```'))

            # Add generated data to memory
            for key, value in customer_data.items():
                if isinstance(value, list):
                    for item in value:
                        self.memory.add(
                            json.dumps(item), 
                            user_id=user_id, 
                            metadata={"app_id": self.app_id, "role": "system"}
                        )
                else:
                    self.memory.add(
                        f"{key}: {json.dumps(value)}", 
                        user_id=user_id, 
                        metadata={"app_id": self.app_id, "role": "system"}
                    )

            return customer_data
        except Exception as e:
            st.error(f"Failed to generate synthetic data: {e}")
            return None

# Initialize the CustomerSupportAIAgent
support_agent = CustomerSupportAIAgent()

# Sidebar for customer ID and memory view
st.sidebar.title("Enter your Customer ID:")
previous_customer_id = st.session_state.get("previous_customer_id", None)
customer_id = st.sidebar.text_input("Enter your Customer ID")

if customer_id != previous_customer_id:
    st.session_state.messages = []
    st.session_state.previous_customer_id = customer_id
    st.session_state.customer_data = None

# Add button to generate synthetic data
if st.sidebar.button("Generate Synthetic Data"):
    if customer_id:
        with st.spinner("Generating customer data..."):
            st.session_state.customer_data = support_agent.generate_synthetic_data(customer_id)
        if st.session_state.customer_data:
            st.sidebar.success("Synthetic data generated successfully!")
        else:
            st.sidebar.error("Failed to generate synthetic data.")
    else:
        st.sidebar.error("Please enter a customer ID first.")

if st.sidebar.button("View Customer Profile"):
    if st.session_state.customer_data:
        st.sidebar.json(st.session_state.customer_data)
    else:
        st.sidebar.info("No customer data generated yet. Click 'Generate Synthetic Data' first.")

if st.sidebar.button("View Memory Info"):
    if customer_id:
        memories = support_agent.get_memories(user_id=customer_id)
        if memories:
            st.sidebar.write(f"Memory for customer **{customer_id}**:")
            if memories and "results" in memories:
                for memory in memories["results"]:
                    if "memory" in memory:
                        st.sidebar.markdown(f"- {memory['memory']}")
        else:
            st.sidebar.info("No memory found for this customer ID.")
    else:
        st.sidebar.error("Please enter a customer ID to view memory info.")

# Initialize the chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display the chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
query = st.chat_input("How can I assist you today?")

if query and customer_id:
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    # Generate and display response
    with st.spinner("Generating response..."):
        answer = support_agent.handle_query(query, user_id=customer_id)

    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": answer})
    with st.chat_message("assistant"):
        st.markdown(answer)

elif query and not customer_id:
    st.error("Please enter a customer ID to start the chat.")