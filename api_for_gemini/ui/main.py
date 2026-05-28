import mesop as me
import mesop.components.text as mt


@me.page(path="/")
def page():
    with me.box(style=me.Style(padding=me.Padding.all(24))):
        me.text("API for Gemini - UI", type="headline-3")
        me.text("Welcome to the Gemini API Proxy UI.")

        with me.box(style=me.Style(margin=me.Margin(top=24))):
            me.text("Current Status:", type="headline-6")
            me.text("Proxy server is managed via the CLI: 'gema start'")

        with me.box(style=me.Style(margin=me.Margin(top=24))):
            me.text("Available Features (Planned):", type="headline-6")
            with me.box(style=me.Style(margin=me.Margin(left=16))):
                me.text("- Configuration Editor")
                me.text("- Real-time Log Viewer")
                me.text("- Model Routing Rules Tester")


@me.page(path="/chat")
def chat_page():
    with me.box(style=me.Style(padding=me.Padding.all(24))):
        me.text("Chat Interface (WIP)", type="headline-3")
        me.text("This will allow you to test your proxy directly.")
