import gradio as gr
from func import *

args = normal.get_args()
llm_instance = run(args)

def main():
    with gr.Blocks(css="footer {visibility: hidden}") as demo:
        gr.Markdown("""<center><font size=10>Data Agent</center>""")
        with gr.Row(equal_height=False):
            file_output = gr.Files(height=200)
            df_process = gr.DataFrame(scale=1, height=350,interactive=False,wrap=True)
        with gr.Row(equal_height=False):
            
            df = gr.outputs.Dataframe(type='pandas')
            gallery = gr.Gallery(label="plots of the data",preview = False).style(height='auto',columns=2)
        with gr.Row(equal_height=False):
                chatbot = gr.Chatbot(label='final report',scale=1)
                with gr.Column():
                    textbox_out = gr.Textbox(lines=3, label='SQL statement generated by llms')
                    textbox = gr.Textbox(lines=3, label='send your question about the data')
                    with gr.Row():
                        clear_history = gr.Button("🧹 clear")
                        sumbit = gr.Button("🚀 submit")
        file_output.upload(llm_instance.process_file, inputs= [file_output],outputs=[df_process])
        sumbit.click(llm_instance.model_chat, [textbox, chatbot, df_process], [textbox_out, chatbot, gallery, df])
        clear_history.click(fn=normal.clear_session,
                            inputs=[],
                            outputs=[textbox, textbox_out, chatbot, gallery, df, df_process])
    demo.queue(api_open=False).launch(max_threads=10, height=800, share=False)
if __name__ == "__main__":
    main()