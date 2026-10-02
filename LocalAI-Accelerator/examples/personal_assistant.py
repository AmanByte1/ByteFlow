"""
Personal Assistant Example - Using LocalAI Accelerator

This example shows how to build a personal AI assistant
that responds to voice commands and questions locally.
"""

from local_ai_accelerator import LocalAIAccelerator
from datetime import datetime
import json


class PersonalAssistant:
    """Simple local AI personal assistant"""
    
    def __init__(self, model_name: str = "phi-2"):
        """Initialize the assistant"""
        self.accelerator = LocalAIAccelerator()
        self.model_name = model_name
        self.conversation_history = []
        
        # Load model
        print(f"Loading {model_name}...")
        if not self.accelerator.load_model(model_name):
            raise RuntimeError(f"Failed to load {model_name}")
        
        print("✅ Assistant ready!")
    
    def chat(self, user_message: str, context: str = "") -> str:
        """Chat with the assistant"""
        
        # Add to history
        self.conversation_history.append({
            "role": "user",
            "message": user_message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Build context
        context_str = context or self._get_context()
        
        # Create prompt
        prompt = f"""You are a helpful personal assistant.
Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Context: {context_str}

Conversation so far:
"""
        
        # Add recent history
        for item in self.conversation_history[-3:]:
            prompt += f"\nUser: {item['message']}"
        
        prompt += f"\n\nRespond helpfully and concisely:"
        
        # Get response
        response = self.accelerator.inference(
            prompt=prompt,
            model_name=self.model_name,
            max_tokens=256,
            temperature=0.7
        )
        
        # Add to history
        self.conversation_history.append({
            "role": "assistant",
            "message": response,
            "timestamp": datetime.now().isoformat()
        })
        
        return response
    
    def answer_question(self, question: str) -> str:
        """Answer a specific question"""
        prompt = f"Answer this question concisely: {question}"
        return self.accelerator.inference(
            prompt=prompt,
            model_name=self.model_name,
            max_tokens=200
        )
    
    def summarize(self, text: str) -> str:
        """Summarize text"""
        prompt = f"Summarize this text in 2-3 sentences:\n{text}"
        return self.accelerator.inference(
            prompt=prompt,
            model_name=self.model_name,
            max_tokens=150
        )
    
    def translate(self, text: str, target_language: str) -> str:
        """Translate text"""
        prompt = f"Translate to {target_language}:\n{text}"
        return self.accelerator.inference(
            prompt=prompt,
            model_name=self.model_name,
            max_tokens=200
        )
    
    def brainstorm(self, topic: str, num_ideas: int = 5) -> list:
        """Generate ideas on a topic"""
        prompt = f"Generate {num_ideas} creative ideas about: {topic}"
        response = self.accelerator.inference(
            prompt=prompt,
            model_name=self.model_name,
            max_tokens=300
        )
        return response.split('\n')
    
    def explain(self, concept: str) -> str:
        """Explain a concept simply"""
        prompt = f"Explain {concept} to a 10-year-old child simply:"
        return self.accelerator.inference(
            prompt=prompt,
            model_name=self.model_name,
            max_tokens=256
        )
    
    def _get_context(self) -> str:
        """Get current context information"""
        time_of_day = "morning" if datetime.now().hour < 12 else "afternoon" if datetime.now().hour < 18 else "evening"
        return f"It's {time_of_day}. You are being helpful and friendly."
    
    def get_stats(self) -> dict:
        """Get assistant statistics"""
        return {
            "model": self.model_name,
            "messages": len(self.conversation_history),
            "resource_stats": self.accelerator.get_resource_stats()
        }
    
    def reset_conversation(self):
        """Reset conversation history"""
        self.conversation_history = []
    
    def save_conversation(self, filename: str):
        """Save conversation to file"""
        with open(filename, 'w') as f:
            json.dump(self.conversation_history, f, indent=2)
        print(f"Conversation saved to {filename}")
    
    def shutdown(self):
        """Clean up"""
        self.accelerator.shutdown()


# Interactive chat mode
def interactive_mode():
    """Run assistant in interactive mode"""
    assistant = PersonalAssistant()
    
    print("\n" + "="*60)
    print("Personal AI Assistant")
    print("="*60)
    print("Commands:")
    print("  'question: ...' - Ask a question")
    print("  'summarize: ...' - Summarize text")
    print("  'explain: ...' - Explain a concept")
    print("  'brainstorm: ...' - Generate ideas")
    print("  'stats' - Show statistics")
    print("  'clear' - Reset conversation")
    print("  'exit' - Quit")
    print("="*60 + "\n")
    
    try:
        while True:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == 'exit':
                print("Goodbye!")
                break
            
            elif user_input.lower() == 'stats':
                stats = assistant.get_stats()
                print(f"\nAssistant stats:")
                print(f"  Model: {stats['model']}")
                print(f"  Messages: {stats['messages']}")
                print(f"  CPU: {stats['resource_stats']['cpu_percent']:.1f}%")
                if stats['resource_stats']['gpu_percent']:
                    print(f"  GPU: {stats['resource_stats']['gpu_percent']:.1f}%")
                print()
            
            elif user_input.lower() == 'clear':
                assistant.reset_conversation()
                print("Conversation cleared.\n")
            
            elif user_input.lower().startswith('question:'):
                question = user_input[9:].strip()
                print(f"\nAssistant: {assistant.answer_question(question)}\n")
            
            elif user_input.lower().startswith('summarize:'):
                text = user_input[10:].strip()
                print(f"\nAssistant: {assistant.summarize(text)}\n")
            
            elif user_input.lower().startswith('explain:'):
                concept = user_input[8:].strip()
                print(f"\nAssistant: {assistant.explain(concept)}\n")
            
            elif user_input.lower().startswith('brainstorm:'):
                topic = user_input[11:].strip()
                ideas = assistant.brainstorm(topic)
                print(f"\nIdeas about {topic}:")
                for idea in ideas:
                    if idea.strip():
                        print(f"  • {idea.strip()}")
                print()
            
            else:
                response = assistant.chat(user_input)
                print(f"\nAssistant: {response}\n")
    
    finally:
        assistant.shutdown()


# Programmatic usage
def programmatic_example():
    """Example of using assistant programmatically"""
    assistant = PersonalAssistant()
    
    # Get a summary
    text = "Artificial Intelligence is transforming industries across the world..."
    summary = assistant.summarize(text)
    print(f"Summary: {summary}")
    
    # Answer questions
    response = assistant.answer_question("What is machine learning?")
    print(f"Response: {response}")
    
    # Generate ideas
    ideas = assistant.brainstorm("sustainable energy", num_ideas=3)
    print(f"Ideas: {ideas}")
    
    assistant.shutdown()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--programmatic":
        programmatic_example()
    else:
        interactive_mode()
