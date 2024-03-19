from openai import OpenAI
from prompt import prompt_manager
import json, argparse
from pandasql import sqldf
from auto_plot_mat import plot_data
import pandas as pd
class normal:
    def __init__(self) -> None:
        pass
    @staticmethod
    def clear_session():
        """
        Clear the current session.

        Returns:
            Tuple[str, List]: A tuple containing an empty string and an empty list.

        """
        return '','', [], [], pd.DataFrame(),pd.DataFrame()
    @staticmethod
    def get_args():
        """
        Parse command line arguments using argparse.

        Returns:
            argparse.Namespace: An object containing parsed arguments.

        """
        # Create ArgumentParser object
        parser = argparse.ArgumentParser()
        # Add command line arguments
        parser.add_argument("--openai_key", type=str,
                        default="", help="API key for OpenAI API")
        parser.add_argument("--api_base", type=str,
                        default='', help="api_base that can util the llm in local api")
        parser.add_argument("--openai_engine", type=str,
                        default="gpt-3.5-turbo", help="large language model's engine")
        parser.add_argument("--debug_depth", type=int,
                        default=3, help="Debug depth for regenerate SQL by the llm")
        parser.add_argument("--temperature", type=float,
                        default=0.5, help="Temperature setting for the large language model")
        
        # Parse the arguments
        args = parser.parse_args()
        return args
class data_agent(prompt_manager):
    def __init__(self, args):
        super().__init__()
        self.args = args
    def process_file(self, file):
        """
        Process a file or list of files.

        Args:
            file (gradio's file or a list): A gradio's file or a list of gradio's files.

        Returns:
            pd.DataFrame: A DataFrame containing information about the file's schema's info generated by the llm.

        """
        if not isinstance(file, list):
            file = [file]
        df = pd.DataFrame()
        for i in range(len(file)):
            file_name = file[i].name
            data_temp = {'new_df' + str(i): {'type': file_name, 'description': '-'*10}}
            df_temp = pd.DataFrame.from_dict(data_temp, orient='index').reset_index()
            df = pd.concat([df, df_temp], axis=0, ignore_index=True)
            df_real = pd.read_csv(file_name)
            schema_info = self.generate_schema(df_real)
            df_schema = pd.DataFrame.from_dict(schema_info, orient='index').reset_index()
            df = pd.concat([df, df_schema], axis=0, ignore_index=True)
            df = df[['index','description','type']]
        return df
    def run_llm(self, query, history = []):
        """
        Run the language model to generate a response based on the given query and conversation history.

        Args:
            query (str): The user's query.
            openai_key (str): The API key for OpenAI.
            api_base (str): The base URL for the OpenAI API.
            engine (str): The engine to use for the language model.
            history (list): A list of dictionaries representing the conversation history.

        Returns:
            str: The generated response from the language model.

        """
        openai_key = self.args.openai_key
        api_base = self.args.api_base
        temperature = self.args.temperature
        engine = self.args.openai_engine
        if api_base == '':
            client = OpenAI(api_key=openai_key)
        else:
            client = OpenAI(api_key=openai_key, base_url=api_base)
        messages = [{"role":"system","content":"You are an useful AI assistant that helps people solve the problem step by step."}]
        messages.extend(history)
        message_prompt = {"role":"user","content":query}
        messages.append(message_prompt)
        response = client.chat.completions.create(
                        model=engine,
                        messages = messages,
                        temperature=temperature,
                        frequency_penalty=0,
                        presence_penalty=0)
        result = response.choices[0].message.content
        return result
    def generate_schema(self, df_real):
        """
        Generate schema information for a given DataFrame.

        Args:
            df_real (pd.DataFrame): The DataFrame for which to generate schema information.

        Returns:
            dict: A dictionary containing schema information for each column.

        """
        df_string = df_real.head().to_string()
        prompt = self.schema_prompt.format(df_string)
        schema_info = self.run_llm(prompt)

        try:
            result = json.loads(schema_info.replace("'", "\""))
        
        except Exception as e:
            result = {}
            column_types = df_real.dtypes
            for col in df_real.columns:
                result[col] = {
                    "type": str(column_types[col]),
                    "description": str(df_real[col][0])  # 使用第一行的数据作为描述
                }
            print(f"a error occured when transfer the schema_info string to dict: {e}, it will use the row's data to be the description")

        return result
    def generate_sql(self, query, table_name, schema, history = [], debug = False, error =''):
        """
        Generate SQL code based on user query, table name, and schema. Can debug and regenerate the SQL with llm when setting the debug == True and giving the error message.

        Args:
            query (str): The user's query.
            table_name (str): The name of the table.
            schema (dict): The schema of the table.
            history (list, optional): A list of dictionaries representing the conversation history. Defaults to [].
            debug (bool, optional): Whether to run in debug mode. Defaults to False.
            error (str, optional): The error message, if any. Defaults to ''.

        Returns:
            tuple: A tuple containing the generated SQL code and updated history.

        """
        if not debug:
            prompt_content = self.sql_prompt.format(query, table_name, schema)
            answer = self.run_llm(prompt_content)
            history.append({'role':'user',"content":prompt_content})
            history.append({'role':'assistant',"content":answer})
            print(f'sql_answer******************{answer}')
            return answer, history
        else:
            prompt_debug = self.prompt_debug
            sql_before = error.split('...')[1]
            e = error.split('...')[0]
            prompt_debug_content = prompt_debug.format(sql_before, e)
            answer_debug = self.srun_llm(prompt_debug_content, history=history)
            history.append({'role':'user',"content":prompt_debug_content})
            history.append({'role':'assistant',"content":answer_debug})
            return answer_debug, history
class run(data_agent, plot_data, normal):
    def __init__(self, args):
        super(run, self).__init__(args)
        # super().__init__(args)

    def model_chat(self, query: str, history, df_process):
        """
        Chat with the model, generate dataframe's schema; generate SQL statement; execute SQL; debug and regenerate SQL; Report and Visualization.

        Args:
            query (str): The user's query.
            history (Optional[List]): A list of dictionaries representing conversation history.
            df_process (pd.DataFrame): The DataFrame containing process information.

        Returns:
            Tuple[str, List, List, pd.DataFrame]: A tuple containing an empty string,
                conversation responses, image arrays, and the resulting DataFrame from SQL query.
        """

        split_indices = df_process.index[df_process['description'] == '-'*10].tolist()
        paths = []
        if not split_indices:
            dfs = [df_process]
        else:
            dfs = []
            start_idx = 0
            for end_idx in split_indices:
                if end_idx != 0:
                    dfs.append(df_process.iloc[start_idx:end_idx])
                start_idx = end_idx + 1
                paths.append(df_process.loc[end_idx, 'type'])
            dfs.append(df_process.iloc[start_idx:])
        table = []
        scema = ''
        for i, d in enumerate(dfs):
            df_name_str = "df_use_" + str(i+1)
            table.append(df_name_str)
            locals()[df_name_str] = pd.read_csv(paths[i])
            scema_temp = d.set_index('index').to_dict(orient='index')
            scema += df_name_str + '的schema:' + '\n\n' + str(scema_temp) + '\n\n'
        table_name = ','.join(table)
        
        sql_statement, sql_history = self.generate_sql(query, table_name, scema)
        sql_output = 'SQL statement: \n' + sql_statement
        df_temp_yield = pd.DataFrame()
        yield sql_output, '', [], df_temp_yield
        i = 0
        while i < self.args.debug_depth:
            try:
                pandaSQL_solution = sqldf(sql_statement, locals())
                yield sql_output, '', [], pandaSQL_solution
                break
            except Exception as e:
                debug_message = f"there're bugs in sql, debuging by the gpt at the {i+1} time......"
                sql_output = sql_output + '\n' + '********************' + debug_message +'\n'
                e = str(e) + '...' + str(sql_statement)
                sql_statement, sql_history = self.generate_sql(query, table_name, scema, history=sql_history, debug=True, error = e)
                sql_output += sql_statement
                yield sql_output, '', [], df_temp_yield
            i+=1

        
        image_arrays = self.auto_plot(df=pandaSQL_solution)
        yield sql_output, '', image_arrays, pandaSQL_solution
        mylist = list()
        mylist.append(query)
        prompt_list = [query]
        string_data = pandaSQL_solution.to_string()
        prompt_list.append(sql_statement)
        prompt_list.append(string_data)
        prompt_report = self.prompt_report.format(str(prompt_list))
        report_answer = self.run_llm(query=prompt_report)
        mylist.append(report_answer)
        responses = list()
        if len(history) > 0:
            for history_msg in history:
                responses.append(history_msg)
        responses.append(mylist)
        
        yield sql_output, responses, image_arrays, pandaSQL_solution

