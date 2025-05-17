# Project Structure

```
/  
|-- examples/  
|   |-- __init__.py
|   |-- data_factory.ipynb
|   |-- structured_llm.ipynb
|   |-- usecases/  
|       |-- math_data_gen.ipynb
|-- internal/  
|   |-- generate_data_with_topic.ipynb
|   |-- trial_llm.py
|   |-- data_factory_dup.py
|   |-- test_langgraph_structured_llm.py
|   |-- test_langgraph.py
|   |-- test.py
|   |-- README.md
|   |-- starfish.drawio
|   |-- .git
|   |-- simple_feedback_loop.py
|-- src/  
|   |-- starfish/  
|       |-- __init__.py
|       |-- llm/  
|       |   |-- model_hub/  
|       |   |   |-- huggingface_adapter.py
|       |   |-- proxy/  
|       |   |   |-- litellm_adapter.py
|       |   |   |-- litellm_adapter_ext.py
|       |   |-- structured_llm.py
|       |   |-- backend/  
|       |   |   |-- ollama_adapter.py
|       |   |-- parser/  
|       |   |   |-- json_builder.py
|       |   |   |-- __init__.py
|       |   |   |-- pydantic_parser.py
|       |   |   |-- json_parser.py
|       |   |-- prompt/  
|       |   |   |-- __init__.py
|       |   |   |-- prompt_loader.py
|       |   |   |-- prompt_template.py
|       |   |-- utils.py
|       |-- data_ingest/  
|       |   |-- ingest.py
|       |   |-- parsers/  
|       |   |   |-- pdf_parser.py
|       |   |   |-- ppt_parser.py
|       |   |   |-- html_parser.py
|       |   |   |-- excel_parser.py
|       |   |   |-- docx_parser.py
|       |   |   |-- __init__.py
|       |   |   |-- base_parser.py
|       |   |   |-- youtube_parser.py
|       |   |   |-- txt_parser.py
|       |   |   |-- google_drive_parser.py
|       |   |   |-- web_parser.py
|       |   |   |-- unstructured_parser.py
|       |   |-- splitter/  
|       |   |   |-- token_splitter.py
|       |   |   |-- simple_splitter.py
|       |   |   |-- base_splitter.py
|       |   |-- utils/  
|       |   |   |-- util.py
|       |   |-- formatter/  
|       |       |-- template_format.py
|       |-- data_mcp/  
|       |   |-- agent_client.py
|       |   |-- server.py
|       |   |-- client.py
|       |-- data_template/  
|       |   |-- utils/  
|       |   |   |-- error.py
|       |   |-- examples.py
|       |   |-- mcp_base.py
|       |   |-- templates/  
|       |   |   |-- starfish/  
|       |   |   |   |-- math_problem_gen_wf.py
|       |   |   |   |-- get_city_info_wf.py
|       |   |   |-- community/  
|       |   |       |-- topic_generator.py
|       |   |       |-- topic_generator_success.py
|       |   |-- template_gen.py
|       |-- components/  
|       |   |-- __init__.py
|       |   |-- prepare_topic.py
|       |-- common/  
|       |   |-- logger.py
|       |   |-- exceptions.py
|       |   |-- env_loader.py
|       |-- telemetry/  
|       |   |-- __init__.py
|       |   |-- posthog_client.py
|       |-- data_factory/  
|           |-- config.py
|           |-- constants.py
|           |-- task_runner.py
|           |-- job_manager_re_run.py
|           |-- utils/  
|           |   |-- enums.py
|           |   |-- util.py
|           |   |-- decorator.py
|           |   |-- data_class.py
|           |   |-- errors.py
|           |   |-- state.py
|           |   |-- mock.py
|           |-- job_manager.py
|           |-- factory.py
|           |-- storage/  
|           |   |-- models.py
|           |   |-- registry.py
|           |   |-- in_memory/  
|           |   |   |-- in_memory_storage.py
|           |   |-- local/  
|           |       |-- data_handler.py
|           |       |-- __init__.py
|           |       |-- local_storage.py
|           |       |-- setup.py
|           |       |-- utils.py
|           |       |-- metadata_handler.py
|           |-- base.py
|           |-- factory_executor_manager.py
|           |-- job_manager_dry_run.py
|           |-- event_loop.py
|           |-- factory_wrapper.py
|           |-- factory_.py
|-- tests/  
|   |-- conftest.py
|   |-- llm/  
|   |   |-- __init__.py
|   |   |-- parser/  
|   |   |   |-- __init__.py
|   |   |   |-- test_json_parser.py
|   |   |   |-- fixtures/  
|   |   |       |-- json_problem_cases.py
|   |   |-- test_pydantic_parser.py
|   |   |-- prompt/  
|   |       |-- test_prompt.py
|   |       |-- __init__.py
|   |       |-- test_prompt_loader.py
|   |-- data_ingest/  
|   |   |-- test_data/  
|   |   |   |-- output/  
|   |   |       |-- gina_ai.txt
|   |   |   |-- input/  
|   |   |-- test_ingest.py
|   |-- pytest.ini
|   |-- data_template/  
|   |   |-- test_data_template.py
|   |   |-- __init__.py
|   |-- __init__.py
|   |-- test_notebooks.py
|   |-- data_factory/  
|       |-- __init__.py
|       |-- storage/  
|       |   |-- __init__.py
|       |   |-- README.md
|       |   |-- local/  
|       |       |-- __init__.py
|       |       |-- test_performance.py
|       |       |-- test_basic_storage.py
|       |       |-- test_local_storage.py
|       |   |-- test_storage_main.py
|       |-- factory/  
|           |-- test_output_index.py
|           |-- test_run.py
|           |-- __init__.py
|           |-- test_dead_queue.py
|           |-- test_resume.py
|           |-- test_resume_duplicate_indices.py
|           |-- test_resume_index.ipynb
|-- .env.template
|-- .gitignore
|-- .gitmodules
|-- LICENSE
|-- Makefile
|-- pyproject.toml
|-- README.md
|-- poetry.lock
|-- .pre-commit-config.yaml
|-- pytest.ini
```
