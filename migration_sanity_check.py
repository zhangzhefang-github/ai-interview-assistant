import os
from dotenv import load_dotenv

def run_checks():
    print("Running LangChain and Pydantic v2 migration sanity checks...")
    
    # Load environment variables (especially for OpenAI API keys if needed for instantiation)
    # Ensure .env is in the same directory as this script or adjust path
    dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
        print(f".env file found and loaded from: {dotenv_path}")
    else:
        # Fallback to loading .env from current working directory if script is not in project root
        load_dotenv()
        print(f"Attempted to load .env from current working directory: {os.getcwd()}")

    print(f"OPENAI_API_KEY loaded: {bool(os.getenv('OPENAI_API_KEY'))}")
    print(f"OPENAI_API_BASE loaded: {bool(os.getenv('OPENAI_API_BASE'))}")
    print(f"DASHSCOPE_API_KEY loaded: {bool(os.getenv('DASHSCOPE_API_KEY'))}")


    # 1. Test LangChain Core Components
    print("\\n--- Testing LangChain Core ---")
    try:
        from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.messages import HumanMessage, SystemMessage
        
        print("Successfully imported LangChain core components.")

        # Test ChatPromptTemplate
        prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template("You are a helpful assistant that translates {input_language} to {output_language}."),
            HumanMessagePromptTemplate.from_template("{text}")
        ])
        formatted_prompt = prompt.format_messages(input_language="English", output_language="French", text="Hello world")
        assert len(formatted_prompt) == 2
        assert isinstance(formatted_prompt[0], SystemMessage)
        assert isinstance(formatted_prompt[1], HumanMessage)
        print("ChatPromptTemplate basic formatting test passed.")

        # Test StrOutputParser
        parser = StrOutputParser()
        print("StrOutputParser instantiated.")

    except ImportError as e:
        print(f"Error importing LangChain components: {e}")
    except Exception as e:
        print(f"Error during LangChain core tests: {e}")

    # 2. Test LangChain OpenAI
    print("\\n--- Testing LangChain OpenAI ---")
    try:
        from langchain_openai import ChatOpenAI
        print("Successfully imported ChatOpenAI.")
        
        if not os.getenv('OPENAI_API_KEY'):
            print("OPENAI_API_KEY not set. Skipping ChatOpenAI instantiation and invocation.")
        else:
            llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
            print("ChatOpenAI instantiated successfully.")
            
            # Optional: Test invocation if you want to ensure API call works
            # try:
            #     response = llm.invoke("Hello, world!")
            #     print(f"ChatOpenAI invocation response: {response.content[:50]}...")
            #     assert response.content is not None
            # except Exception as e:
            #     print(f"ChatOpenAI invocation failed (API call error): {e}")

    except ImportError as e:
        print(f"Error importing LangChain OpenAI components: {e}")
    except Exception as e:
        print(f"Error during LangChain OpenAI tests: {e}")
    
    # 2.1 Test LangChain Community (Example: DashScope - Tongyi Qwen)
    print("\\n--- Testing LangChain Community (DashScope Tongyi Qwen) ---")
    try:
        from langchain_community.chat_models.tongyi import ChatTongyi
        print("Successfully imported ChatTongyi from langchain_community.")

        if not os.getenv('DASHSCOPE_API_KEY'):
            print("DASHSCOPE_API_KEY not set. Skipping ChatTongyi instantiation.")
        else:
            # Ensure you have `dashscope` installed: `pip install dashscope`
            try:
                dash_llm = ChatTongyi(model_name="qwen-turbo") 
                print("ChatTongyi (qwen-turbo) instantiated successfully.")
                # Optional: Test invocation
                # response_dash = dash_llm.invoke("你好，世界！")
                # print(f"ChatTongyi invocation response: {response_dash.content[:50]}...")
                # assert response_dash.content is not None
            except Exception as e:
                print(f"Error instantiating or invoking ChatTongyi: {e}")
                print("Make sure you have the 'dashscope' library installed (`uv pip install dashscope`) and DASHSCOPE_API_KEY is valid.")

    except ImportError as e:
        print(f"Error importing LangChain Community components (ChatTongyi): {e}")
        print("This might be because 'langchain-community' or its specific dependencies are not installed correctly, or the module path has changed.")
    except Exception as e:
        print(f"Error during LangChain Community (ChatTongyi) tests: {e}")


    # 3. Test Pydantic v2
    print("\\n--- Testing Pydantic v2 ---")
    try:
        from pydantic import BaseModel, Field, ValidationError
        from typing import Optional, List
        from datetime import datetime

        print("Successfully imported Pydantic components.")

        class ItemV2(BaseModel):
            name: str
            description: Optional[str] = None
            price: float = Field(gt=0)
            tags: List[str] = []
            created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

        item_data_valid = {"name": "Test Item", "price": 10.99, "tags": ["test", "pydantic_v2"]}
        item = ItemV2(**item_data_valid)
        assert item.name == "Test Item"
        assert item.price == 10.99
        assert item.created_at is not None
        print("Pydantic model (ItemV2) instantiation with valid data passed.")

        try:
            ItemV2(name="Invalid Item", price=-1.0) # type: ignore
            print("Pydantic validation error: Expected failure for price <= 0, but it passed.")
        except ValidationError as e:
            print(f"Pydantic validation for invalid price correctly raised ValidationError: {len(e.errors())} error(s).")
            assert len(e.errors()) == 1
            error_detail = e.errors()[0]
            # In Pydantic V2, type might be 'greater_than' or similar specific to the constraint
            assert 'type' in error_detail and 'greater_than' in error_detail['type']
            print(f"Validation error details: {error_detail}")


        item_json = item.model_dump_json() 
        print(f"Pydantic model_dump_json() output: {item_json[:100]}...")
        assert "Test Item" in item_json
        
        item_dict = item.model_dump() 
        assert item_dict['name'] == "Test Item"
        print("Pydantic model serialization (model_dump_json, model_dump) tests passed.")
        
        re_item = ItemV2.model_validate_json(item_json) 
        assert re_item.name == item.name
        print("Pydantic model parsing (model_validate_json) test passed.")


    except ImportError as e:
        print(f"Error importing Pydantic components: {e}")
    except Exception as e:
        print(f"Error during Pydantic v2 tests: {e}")

    # 4. Test Pydantic Settings (if used for configuration)
    print("\\n--- Testing Pydantic Settings (pydantic-settings) ---")
    try:
        from pydantic_settings import BaseSettings, SettingsConfigDict
        print("Successfully imported pydantic_settings components.")

        # First, let's test the original AppSettings behavior (it uses the main .env via dotenv_path or its defaults)
        # This class definition is similar to what was there, to show it still works as expected for general use.
        class GlobalAppSettings(BaseSettings):
            APP_NAME: str = "GlobalAppDefault" # Default if not in main .env
            DEBUG_MODE: bool = False          # Default if not in main .env
            # This model_config will use the dotenv_path (main .env file)
            model_config = SettingsConfigDict(env_file=dotenv_path, env_file_encoding='utf-8', extra='ignore')

        global_settings = GlobalAppSettings()
        print(f"GlobalAppSettings (using main .env or defaults) loaded: APP_NAME='{global_settings.APP_NAME}', DEBUG_MODE={global_settings.DEBUG_MODE}")
        # We expect APP_NAME here to be from the project's .env file if set, otherwise "GlobalAppDefault"

        # Now, for a more isolated test of loading from a specific temporary .env file:
        temp_test_env_filename = ".test_isolated_env_file"
        # Define the path *before* the class that uses it in its model_config
        temp_test_env_path = os.path.join(os.path.dirname(__file__), temp_test_env_filename)
        
        with open(temp_test_env_path, "w") as f:
            f.write("SPECIFIC_TEST_APP_NAME=ValueFromIsolatedFile\n")
            f.write("SPECIFIC_TEST_DEBUG_MODE=True\n")

        # Define the class AFTER temp_test_env_path is known, so it can be used in model_config
        class IsolatedTestSettings(BaseSettings):
            SPECIFIC_TEST_APP_NAME: str = "DefaultSpecificApp" # Default if not in the specific .env
            SPECIFIC_TEST_DEBUG_MODE: bool = False         # Default if not in the specific .env
            
            model_config = SettingsConfigDict(
                env_file=temp_test_env_path, # Correctly use the dynamic path here
                env_file_encoding='utf-8',
                extra='ignore' # Ignore any other variables in the .env file not defined in the model
            )
        
        # Instantiate without passing model_config, as it's now part of the class definition
        isolated_settings = IsolatedTestSettings()
        
        print(f"IsolatedTestSettings loaded from '{temp_test_env_path}': "
              f"SPECIFIC_TEST_APP_NAME='{isolated_settings.SPECIFIC_TEST_APP_NAME}', "
              f"SPECIFIC_TEST_DEBUG_MODE={isolated_settings.SPECIFIC_TEST_DEBUG_MODE}")
        
        assert isolated_settings.SPECIFIC_TEST_APP_NAME == "ValueFromIsolatedFile"
        assert isolated_settings.SPECIFIC_TEST_DEBUG_MODE is True
        
        os.remove(temp_test_env_path)
        print(f"Pydantic-settings loading from isolated temp .env file ('{temp_test_env_path}') test passed.")

    except ImportError:
        print("pydantic_settings not found. If not used, this is fine. Otherwise, install it (`uv pip install pydantic-settings`).")
    except Exception as e:
        print(f"Error during Pydantic Settings tests: {e}")

    print("\\nSanity checks completed.")

if __name__ == "__main__":
    run_checks() 