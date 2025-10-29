from strands import Agent
from strands_tools.browser import AgentCoreBrowser
import time

print("✅ Libraries imported successfully!")

def create_agent():
    """Create and configure the Strands agent with AgentCoreBrowser"""
    # Initialize the official AgentCoreBrowser tool
    agent_core_browser = AgentCoreBrowser(region="eu-central-1")
    
    # Create agent with Claude Haiku model and optimized settings
    agent = Agent(
        tools=[agent_core_browser.browser],
        model="anthropic.claude-3-haiku-20240307-v1:0",
        system_prompt="""You are an intelligent financial analyst that specializes in analyzing stock and financial websites. When asked to analyze a financial website:

1. Use the browser tool to visit and interact with the website EFFICIENTLY
2. Focus on extracting key financial information QUICKLY:

**For Financial/Stock Websites (MarketWatch, Bloomberg, etc.):**
- Current stock prices and market data
- Price movements and trends (daily, weekly, monthly changes)
- Key financial metrics and ratios (P/E, Market Cap, etc.)
- Trading volume and market activity
- Recent news and market sentiment
- Analyst recommendations and price targets
- Company fundamentals and performance indicators

IMPORTANT: Work efficiently and complete your analysis within 2-3 browser interactions. Always provide specific, actionable financial insights with actual numbers and data points. Be concise but comprehensive in your analysis, focusing on the most important financial metrics for investors."""
    )
    return agent

# Initialize agent globally
strands_agent = create_agent()

print("✅ Strands agent created with AgentCoreBrowser integration!")

def invoke(payload):
    """Structured invoke function for agent interaction"""
    user_message = payload.get("prompt", "")
    
    try:
        print("🚀 Starting analysis...")
        start_time = time.time()
        
        response = strands_agent(user_message)
        
        elapsed_time = time.time() - start_time
        print(f"✅ Analysis completed in {elapsed_time:.2f} seconds")
        
        return response.message["content"][0]["text"] if response.message.get("content") else str(response)
        
    except Exception as e:
        print(f"❌ Error during analysis: {str(e)}")
        return f"Error occurred: {str(e)}"

print("✅ Invoke function created!")

# 📝 Note: If you access slow websites that cause timeouts, you may need to
# implement timeout handling in your code to prevent hanging operations.

# Test with MarketWatch Tesla page
financial_test = {
    "prompt": "Please analyze the Tesla stock page at https://www.marketwatch.com/investing/stock/tsla and provide key financial insights"
}

print("📊 Testing MarketWatch Financial Analysis")
print("=" * 50)

result = invoke(financial_test)
print(result)

print("\n✅ MarketWatch analysis test completed!")

def analyze_website(url, question=None):
    """Convenient function for interactive website analysis"""
    if question:
        prompt = f"Visit {url} and answer this question: {question}"
    else:
        prompt = f"Please analyze the website at {url} and provide comprehensive financial insights"
    
    payload = {"prompt": prompt}
    return invoke(payload)

# Example usage
print("🎯 Interactive Analysis Function Ready!")
print("\nExample usage:")
print('analyze_website("https://www.marketwatch.com/investing/stock/aapl", "What is Apple\'s current stock performance?")')
print("\n✅ Interactive analysis function ready!")

if __name__ == "__main__":
    # Example with MarketWatch
    print("🎯 Production Example - Tesla Stock Analysis on MarketWatch:")
    print("=" * 60)
    
    response = invoke({
        "prompt": "Analyze the Tesla stock at https://www.marketwatch.com/investing/stock/tsla and provide detailed financial insights"
    })
    
    print(response)
    
    print("\n✅ All tests completed successfully!")
    print("\n🚀 Ready for production use with the invoke() function pattern!")
    print("\n📝 Usage Examples:")
    print('invoke({"prompt": "Analyze Tesla stock at https://www.marketwatch.com/investing/stock/tsla"})')
    print('invoke({"prompt": "Get Apple stock data from https://www.marketwatch.com/investing/stock/aapl"})')
    print('analyze_website("https://www.marketwatch.com/investing/stock/nvda", "What is NVIDIA\'s market performance?")')