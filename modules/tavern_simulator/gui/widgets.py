# ************************
# Scrollable Frame Class
#
# Adapted from: https://gist.github.com/mp035/9f2027c3ef9172264532fcd6262f3b01
# ************************
from tkinter import Canvas, Frame, Scrollbar


class ScrollFrame(Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)  # create a frame (self)

        self.canvas = Canvas(self, borderwidth=0)  # place canvas on self
        self.view_port = Frame(self.canvas)  # place a frame on the canvas, this frame will hold the child widgets
        self.vsb = Scrollbar(self, orient="vertical", command=self.canvas.yview)  # place a scrollbar on self
        self.canvas.configure(yscrollcommand=self.vsb.set)  # attach scrollbar action to scroll of canvas

        self.vsb.pack(side="right", fill="y")  # pack scrollbar to right of self
        self.canvas.pack(side="left", fill="both", expand=True)  # pack canvas to left of self and expand to fil
        self.canvas_window = self.canvas.create_window((4, 4), window=self.view_port, anchor="nw",  # add view port frame to canvas
                                                       tags="self.viewPort")

        self.view_port.bind("<Configure>", self.onFrameConfigure)  # bind an event whenever the size of the viewPort frame changes.
        self.canvas.bind("<Configure>", self.onCanvasConfigure)  # bind an event whenever the size of the viewPort frame changes.

        self.onFrameConfigure(None)  # perform an initial stretch on render, otherwise the scroll region has a tiny border until the first resize

    def onFrameConfigure(self, event):
        '''Reset the scroll region to encompass the inner frame'''
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))  # whenever the size of the frame changes, alter the scroll region respectively.

    def onCanvasConfigure(self, event):
        '''Reset the canvas window to encompass inner frame when required'''
        canvas_width = event.width
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)  # whenever the size of the canvas changes alter the window region respectively.
