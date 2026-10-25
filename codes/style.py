"""Matplotlib style matching the TikZ visual system (Helvetica-metric sans, semantic palette)."""
import matplotlib as mpl
from matplotlib import font_manager as fm
for f in ['/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf','/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
          '/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf','/usr/share/fonts/truetype/liberation/LiberationSans-BoldItalic.ttf']:
    try: fm.fontManager.addfont(f)
    except Exception: pass
mpl.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Liberation Sans','DejaVu Sans'],
 'mathtext.fontset':'custom','mathtext.rm':'Liberation Sans','mathtext.it':'Liberation Sans:italic','mathtext.bf':'Liberation Sans:bold',
 'font.size':7,'axes.labelsize':7,'axes.titlesize':7.6,'axes.titleweight':'bold','legend.fontsize':6.6,'xtick.labelsize':6.5,'ytick.labelsize':6.5,
 'axes.linewidth':0.5,'xtick.major.width':0.5,'ytick.major.width':0.5,'xtick.major.size':2.5,'ytick.major.size':2.5,
 'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'savefig.bbox':'tight','savefig.pad_inches':0.015,
 'axes.edgecolor':'#55534E','xtick.color':'#55534E','ytick.color':'#55534E','axes.labelcolor':'#1D1D1B','text.color':'#1D1D1B',
 'axes.titlelocation':'left','axes.titlepad':4})
INK='#1D1D1B'; INK2='#55534E'; MUTED='#9A9893'; RULE='#D6D4CE'; PAPER='#F3F2EF'
AGENT='#2A78D6'; TOOL='#16A06D'; HUMAN='#EB6834'; CHANGE='#C43D8A'
TOOLD='#0E7A52'; HUMAND='#B8471C'
MM=1/25.4
