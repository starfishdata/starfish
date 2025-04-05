
def deduplication_hook(record, state):
    embedding = embedding_model.embed(str(record))
    for each in state['embedding_cache']:
        if cosine_similarity(embedding, each) > 0.9:
            return 'duplicated'
        
    state['embedding_cache'].append(embedding)
    return 'completed'

@data_factory(storage = {'type': 'local', 'path': '/tmp/starfish_test_performance'}, ## in-memor
              state = {}, 
              max_concurrency = 10,
              max_retries = 3,
              on_record_complete_hooks = [deduplication_hook],
              on_record_fail_hooks = [],
              )
def workflow(city, num_records, state):

    pass


## In-memory storage
generated_data = workflow.run(city = ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Miami'])
## generated_data -> list[Record]

## local storage - one more option to retrieve the data
generated_data = workflow.run(city = ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Miami'])
## generated_data -> list[Record]
## local_stroage.retrieve_projecct(project_name = 'starfish_test_performance')
## local_stroage.retrieve_master_job(master_job_id = 'master_job_id')
workflow.run(num_records = 1000)


### Future workflow to add on existing project / data

existing_data = local_stroage.retrieve_projecct(project_name = 'starfish_test_performance')

@data_factory(storage = {'type': 'local', 'path': '/tmp/starfish_test_performance', project_name = 'starfish_test_performance'},
              state = {}, 
              max_concurrency = 10,
              max_retries = 3,
              on_record_complete_hooks = [],
              on_record_fail_hooks = [],
              )
def new_workflow(city, num_records, state):
    ## Genreate country code for each city
    pass



new_workflow.run(existing_data, )


