from preliminary_heights import *
import matplotlib.pyplot as plt

def make():
    rows=csvread(W/'results/all_tree_preliminary_heights.csv');eligible=[r for r in rows if r['qc_screen_eligible']=='True'];eligible.sort(key=lambda r:float(r['preliminary_height_m']))
    for label,arr in [('shortest',eligible[:8]),('tallest',eligible[::-1][:8])]:
        fig,axs=plt.subplots(4,4,figsize=(16,20))
        for n,r in enumerate(arr):
            p=xyz(read(ROOT/'CloudCompare_review_v2'/r['review_ply_filename']));origin=np.array([float(r['stem_foot_x_m']),float(r['stem_foot_y_m']),float(r['estimated_local_ground_z_m'])]);p-=origin
            if len(p)>65000:p=p[np.random.default_rng(6003).choice(len(p),65000,False)]
            d=json.loads((W/'checkpoints'/f"{r['stable_tree_id']}_height.json").read_text());sec=d['stem_sections']
            for j,k in enumerate([0,1]):
                ax=axs[n//2,(n%2)*2+j];ax.scatter(p[:,k],p[:,2],s=.35,c=p[:,2],cmap='viridis',rasterized=True)
                if sec:ax.scatter(np.array([s['center'][k] for s in sec])-origin[k],np.array([s['z'] for s in sec])-origin[2],c='red',s=8)
                ax.scatter([0],[0],c='red',marker='+',s=35);ax.axhline(0,color='brown',lw=.7);ax.set_aspect('equal',adjustable='datalim');ax.set_xlabel('X offset (m)' if k==0 else 'Y offset (m)');ax.set_ylabel('Z above foot ground (m)');ax.set_title(r['stable_tree_id']+' '+r['preliminary_height_m'][:6]+' m '+('XZ' if k==0 else 'YZ'))
        fig.suptitle(label+' candidates: sampled display only; red fitted stem centres; no completeness approval',fontsize=14);fig.tight_layout(rect=[0,0,1,.975]);fig.savefig(W/'qc_figures'/f'{label}_initial_screen.png',dpi=150);plt.close(fig)
if __name__=='__main__':make()
