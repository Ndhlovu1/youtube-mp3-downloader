from django import forms

class YouTubeDownloadForm(forms.Form):
    url = forms.URLField(label="YouTube Video URL", widget=forms.URLInput(attrs={
        "class": "w-full border rounded px-3 py-2",
        "placeholder": "Paste YouTube link here..."
    }))
