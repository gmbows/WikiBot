import matplotlib.pyplot as plt
import numpy as np

def create_bar_chart(title,xlabel,ylabel,xdata,ydata):
	x = np.arange(0,61,10)
	plt.figure(figsize=(10,5))
	plt.tight_layout()
	#plt.gcf().subplots_adjust(bottom=0.25)
	plt.xticks(x, labels=xdata,rotation=0,va="top")
	#plt.figure(figsize=(10,5))
	
	plt.xlabel(xlabel)
	plt.ylabel(ylabel)
	plt.title(title)
	plt.bar(range(len(ydata)), ydata,width=.7,align="center") 
	plt.savefig("chart.png",dpi=100)