import numpy as np
import matplotlib

from matplotlib import rc
from matplotlib import pyplot as plt
from matplotlib import cm
from matplotlib.colors import LogNorm
from matplotlib.font_manager import FontProperties
from astropy.io import fits

from scipy.stats import ks_2samp
from scipy.linalg.basic import LinAlgError
from astroML.plotting import hist as histML

plt.ion()

gz_path = '/Users/willettk/Astronomy/Research/GalaxyZoo'
gzm_path = '%s/gzmainsequence' % gz_path
fig_path = '%s/paper/figures' % gzm_path
fits_path = '%s/fits' % gz_path

aw_tasks = ['t10_arms_winding_'+r for r in ('a28_tight','a29_medium','a30_loose')]
an_tasks = ['t11_arms_number_'+r for r in ('a31_1','a32_2','a33_3','a34_4','a36_more_than_4','a37_cant_tell')]
an_colors = ('red','orange','yellow','green','blue','purple')
aw_colors = ('red','green','blue')

def get_data():

    filename = '%s/mpajhu_gz2.fits' % fits_path

    with fits.open(filename) as f:
        data = f[1].data

    return data

def get_sfr_sample(data):

    # Find starforming galaxies

    sf = (data['bpt'] == 1) #| (data['bpt'] == 2)
    redshift = data['REDSHIFT'] <= 0.1
    absmag = data['PETROMAG_MR'] < -19.5

    sfr_sample = data[sf & redshift]

    return sfr_sample

def get_mass_sfr(sfr_sample):

    mass_sfr_good = (sfr_sample['MEDIAN_MASS'] > -99) & (sfr_sample['MEDIAN_SFR'] > -99)

    mass = sfr_sample[mass_sfr_good]['MEDIAN_MASS']
    sfr = sfr_sample[mass_sfr_good]['MEDIAN_SFR']
    sfr16_err = np.abs(sfr_sample[mass_sfr_good]['P16_SFR'] - sfr_sample[mass_sfr_good]['MEDIAN_SFR'])
    sfr84_err = np.abs(sfr_sample[mass_sfr_good]['P84_SFR'] - sfr_sample[mass_sfr_good]['MEDIAN_SFR']) 
    sfr_err = (sfr16_err + sfr84_err) / 2.

    return mass,sfr,sfr_err

def bins(mass_min=6,mass_max=13,sfr_min=-5,sfr_max=2,nbins=50):

    mass_bins = np.linspace(mass_min,mass_max,nbins)
    sfr_bins = np.linspace(sfr_min,sfr_max,nbins)

    return mass_bins,sfr_bins
    
def fit_mass_sfr(sample,morph,wbe=False,wbm=False):

    # Retrieve mass, star formation rate, and error for subsample from MPA-JHU catalog
    mass,sfr,sfr_err = get_mass_sfr(sample)

    assert wbe != wbm or wbm == False, \
        'Cannot weight both by error and morphology'

    # Weight #1: mean difference between 16th and 84th percentiles to the median value for the weights on fit
    if wbe:
        weights = 1./(sfr_err**2)
        #print 'Using SFR weights'

    # Weight #2: morphological vote fraction
    if wbm:
        weights = sample[(sample['MEDIAN_MASS'] > -99) & (sample['MEDIAN_SFR'] > -99)]['%s_debiased' % morph]
        #print 'Using morphology weights'

    # Weight #3: unweighted
    if not wbe and not wbm:
        weights = None
        #print 'No weights'

    # Find coefficients with polyfit

    (a,b),v = np.polyfit(mass,sfr,1,full=False,w=weights,cov=True)

    return a,b,v

def plot_fits(label,data,axis,color,morph='t11_arms_number_a31_1',lw=2,ls='--',legend=False,verbose=False,weight_by_err=False,weight_by_morph=False):

    if weight_by_err or weight_by_morph:
        prefix = ''
    else:
        prefix = 'un'

    a,b,v = fit_mass_sfr(data,morph,wbe=weight_by_err,wbm=weight_by_morph)
    
    xarr = np.linspace(6,12,100)
    line = axis.plot(xarr,np.polyval([a,b],xarr),color=color,linestyle=ls,linewidth=lw)

    '''
    if legend:
        axis.legend(['weighted','unweighted'],loc=4,shadow=True,fancybox=True,fontsize=10)
    '''

    if verbose:
        print 'Best fit (%10s) for %sweighted data: a,b = %.2f,%.2f' % (label,prefix,a,b)
        print 'Best fit (%10s) for %sweighted data: sigma_a,sigma_b=%.2e,%.2e' % (label,prefix,v[0,0],v[1,1])
        print ''

    return a,b

def plot_ms_arms_number(sfr_sample,weighted=False,contour=False):

    # Plot

    fig = plt.figure(1,(10,6))
    fig.clf()
    filestr=''

    task = 't11_arms_number'

    fig.subplots_adjust(left=0.08,bottom=0.15,right=0.9,hspace=0,wspace=0)

    mass,sfr,sfr_err = get_mass_sfr(sfr_sample)
    mass_bins,sfr_bins = bins()
    h,xedges,yedges = np.histogram2d(mass,sfr,bins=(mass_bins,sfr_bins))

    # Plot each one

    responses = ('a31_1','a32_2','a33_3','a34_4','a36_more_than_4','a37_cant_tell')
    arm_tasks = tuple(['t11_arms_number_'+r for r in responses])
    arm_label = ('1','2','3','4','5+','??')
    colors = ('red','orange','yellow','green','blue','purple')
    for idx, (a,c,al) in enumerate(zip(arm_tasks,colors,arm_label)):

        ax = fig.add_subplot(2,3,idx+1)
        h = ax.hist2d(mass,sfr,bins=50,cmap = cm.gray_r, norm=LogNorm())
        ax.set_xlim(6,11.5)
        ax.set_ylim(-3.9,2)

        if idx == 4:
            ax.set_xlabel('Stellar mass [log '+r'$\/M/M_\odot$]',fontsize=16)
        if idx < 3:
            ax.get_xaxis().set_ticks([])
        if idx == 0 or idx == 3:
            ax.set_ylabel('SFR '+r'$[\log\/M_\odot/\mathrm{yr}]$',fontsize=16)
        else:
            ax.get_yaxis().set_ticks([])


        spiral = (sfr_sample['t01_smooth_or_features_a02_features_or_disk_debiased'] > 0.430) & (sfr_sample['t02_edgeon_a05_no_debiased'] > 0.715) & (sfr_sample['t04_spiral_a08_spiral_weight'] >= 20) & (sfr_sample['t04_spiral_a08_spiral_debiased'] > 0.619)
        n1 = sfr_sample[spiral & (sfr_sample['%s_flag' % a] == 1)] 

        # Two sets of plots: one weights histogram by debiased vote fraction per galaxy; other shows discrete categories from GZ2 flags.
        if weighted:
            filestr='_weighted'
            spirals = sfr_sample[spiral]
            if contour:
                hc,xc,yc = np.histogram2d(spirals['MEDIAN_MASS'],spirals['MEDIAN_SFR'],bins=(mass_bins,sfr_bins),weights=spirals['%s_debiased' % a])
                levels=10**(np.linspace(0,2,8))
                CS = ax.contour(mass_bins[1:],sfr_bins[1:],hc.T,levels,colors=c)
                filestr += '_contour'
            else:
                h = ax.hist2d(spirals['MEDIAN_MASS'],spirals['MEDIAN_SFR'],bins=50,cmap = cm.RdYlGn, weights=spirals['%s_debiased' % a],vmin=0.01,vmax=100.,norm=LogNorm())

            cb_label = r'$w_\mathrm{\phi}$'

            plot_fits(al,spirals,ax,c,morph=a,weight_by_err=False,weight_by_morph=True)
        else:
            ax.scatter(n1['MEDIAN_MASS'],n1['MEDIAN_SFR'], s = 2, color=c, marker='o')
            cb_label = r'$N_\mathrm{star-forming\/galaxies}$'

            plot_fits(al,n1,ax,c)

        ax.text(6.2,1.0,r'$N_{arms} = $%s' % al, color='k',fontsize=18)

        # Plot the linear fits
        plot_fits('SF galaxies',sfr_sample,ax,'black',lw=1,ls='-')

        '''
        # Print number of galaxies in each category

        print '%i %s galaxies' % (len(n1),a)
        '''


    box = ax.get_position()
    axColorbar = plt.axes([box.x0*1.05 + box.width * 0.95, box.y0, 0.01, box.height*2])
    cb = plt.colorbar(h[3],cax = axColorbar, orientation="vertical")
    cb.set_label(r'$N_\mathrm{star-forming\/galaxies}$' ,fontsize=16)

    fig.savefig('%s/ms_arms_number%s.pdf' % (fig_path,filestr), dpi=200)

    return None

def plot_ms_bars(sfr_sample,contour=False):

    # Plot

    fig = plt.figure(2,(11,6))
    fig.clf()
    fig.subplots_adjust(left=0.08,bottom=0.15,right=0.9,hspace=0,wspace=0)
    filestr=''

    mass,sfr,sfr_err = get_mass_sfr(sfr_sample)
    mass_bins,sfr_bins = bins()
    h,xedges,yedges = np.histogram2d(mass,sfr,bins=(mass_bins,sfr_bins))

    notedgeon = (sfr_sample['t01_smooth_or_features_a02_features_or_disk_debiased'] > 0.430) & (sfr_sample['t02_edgeon_a05_no_debiased'] > 0.715) & (sfr_sample['t02_edgeon_a05_no_weight'] >= 20)

    barred = sfr_sample[notedgeon & (sfr_sample['t03_bar_a06_bar_debiased'] >= 0.4)] 
    unbarred = sfr_sample[notedgeon & (sfr_sample['t03_bar_a06_bar_debiased'] < 0.4)] 

    bar_data = (barred,unbarred)
    bar_text = ('Barred','Unbarred')
    color = ('blue','red')

    # Plot barred and unbarred
    for idx, (b,c,t) in enumerate(zip(bar_data,color,bar_text)):

        ax = fig.add_subplot(1,2,idx+1)
        h2 = ax.hist2d(mass,sfr,bins=50,cmap = cm.gray_r, norm=LogNorm())
        ax.set_xlim(6,11.5)
        ax.set_ylim(-4,2)
        ax.set_xlabel('Stellar mass (log '+r'$M/M_\odot$)',fontsize=20)

        if idx == 0:
            ax.set_ylabel('SFR '+r'$[\log\/M_\odot/\mathrm{yr}]$',fontsize=20)
        else:
            ax.get_yaxis().set_ticks([])

        # Try a contour plot??

        if contour:
            hb,xb,yb = np.histogram2d(b['MEDIAN_MASS'],b['MEDIAN_SFR'],bins=(mass_bins,sfr_bins))
            levels=10**(np.linspace(0,2,8))
            CS = ax.contour(mass_bins[1:],sfr_bins[1:],hb.T,levels,colors=c)
            filestr='_contour'
        else:
            ax.scatter(b['MEDIAN_MASS'],b['MEDIAN_SFR'], s=2, color=c, marker='o')

        ax.text(6.2,1.4,t,color=c,fontsize=18)

        # Plot the best linear fit

        plot_fits(t,b,ax,c)
        plot_fits(t,sfr_sample,ax,'black',lw=1,ls='-')

        '''
        # Print counts

        print '%6i %s galaxies' % (len(b),t)
        '''


    box = ax.get_position()
    axColorbar = plt.axes([box.x0*1.05 + box.width * 0.95, box.y0, 0.01, box.height])
    cb = plt.colorbar(h2[3],cax = axColorbar, orientation="vertical")
    cb.set_label(r'$N_\mathrm{star-forming\/galaxies}$' ,fontsize=18)

    fig.savefig('%s/ms_bar%s.pdf' % (fig_path,filestr), dpi=200)

    return None
    
def plot_ms_arms_winding(sfr_sample,weighted=False):

    # Plot

    fig = plt.figure(3,(10,4))
    fig.clf()
    filestr=''

    fig.subplots_adjust(left=0.08,bottom=0.15,hspace=0,wspace=0)

    mass,sfr,sfr_err = get_mass_sfr(sfr_sample)
    mass_bins,sfr_bins = bins()
    h,xedges,yedges = np.histogram2d(mass,sfr,bins=(mass_bins,sfr_bins))

    # Plot each morphological category

    responses = ('a28_tight','a29_medium','a30_loose')
    arm_tasks = tuple(['t10_arms_winding_'+r for r in responses])
    colors = ('red','green','blue')
    for idx, (a,c) in enumerate(zip(arm_tasks,colors)):

        arm_label = a[21:]

        ax = fig.add_subplot(1,3,idx+1)
        h = ax.hist2d(mass,sfr,bins=50,cmap = cm.gray_r, norm=LogNorm())
        ax.set_xlim(6,11.5)
        ax.set_ylim(-4,2)
        if idx == 0:
            ax.set_ylabel('SFR '+r'$[\log\/M_\odot/\mathrm{yr}]$',fontsize=16)
        if idx == 1:
            ax.set_xlabel('Stellar mass [log '+r'$\/M/M_\odot$]',fontsize=16)

        if idx > 0:
            ax.get_yaxis().set_ticks([])

        spiral = (sfr_sample['t01_smooth_or_features_a02_features_or_disk_debiased'] > 0.430) & (sfr_sample['t02_edgeon_a05_no_debiased'] > 0.715) & (sfr_sample['t04_spiral_a08_spiral_weight'] >= 20) & (sfr_sample['t04_spiral_a08_spiral_debiased'] > 0.619)
        n1 = sfr_sample[spiral & (sfr_sample['%s_flag' % a] == 1)] 

        # Two sets of plots: one weights histogram by debiased vote fraction per galaxy; other shows discrete categories from GZ2 flags.
        if weighted:
            spirals = sfr_sample[spiral]
            h = ax.hist2d(spirals['MEDIAN_MASS'],spirals['MEDIAN_SFR'],bins=50,cmap = cm.RdYlGn, weights=spirals['%s_debiased' % a],vmin=0.01,vmax=100.,norm=LogNorm())
            filestr='_weighted'
            cb_label = r'$w_\mathrm{\phi}$'
            plot_fits(arm_label,spirals,ax,c,morph=a,weight_by_err=False,weight_by_morph=True)
        else:
            ax.scatter(n1['MEDIAN_MASS'],n1['MEDIAN_SFR'], s = 2, color=c, marker='o')
            cb_label = r'$N_\mathrm{star-forming\/galaxies}$'
            plot_fits(al,n1,ax,c,morph=a)

        ax.text(6.2,1.3,r'$\phi_{arms} = $%s' % arm_label, color='k')

        # Plot the best linear fits

        plot_fits(arm_label,sfr_sample,ax,'black',lw=1,ls='-')

        '''
        # Print number of galaxies in each category

        print '%i %s galaxies' % (len(n1),a)
        '''

    # Set the colorbar and labels at the end

    box = ax.get_position()
    axColorbar = plt.axes([box.x0*1.05 + box.width * 0.93, box.y0, 0.01, box.height])
    cb = plt.colorbar(h[3],cax = axColorbar, orientation="vertical")
    cb.set_label(cb_label,fontsize=16)

    fig.savefig('%s/ms_arms_winding%s.pdf' % (fig_path,filestr), dpi=200)

    return None

def plot_ms_mergers(sfr_sample):

    # Plot

    fig = plt.figure(4,(10,8))
    fig.clf()

    fig.subplots_adjust(left=0.08,bottom=0.15,hspace=0,wspace=0)

    mass,sfr,sfr_err = get_mass_sfr(sfr_sample)
    mass_bins,sfr_bins = bins()
    h,xedges,yedges = np.histogram2d(mass,sfr,bins=(mass_bins,sfr_bins))

    # Plot star-forming galaxies

    ax = fig.add_subplot(111)
    h = ax.hist2d(mass,sfr,bins=50,cmap = cm.gray_r, norm=LogNorm())
    ax.set_xlim(6,11.5)
    ax.set_ylim(-4,2)
    ax.set_ylabel('log SFR '+r'$[M_\odot/\mathrm{yr}]$',fontsize=16)
    ax.set_xlabel('Stellar mass [log '+r'$\/M/M_\odot$]',fontsize=16)

    # Plot mergers data

    with fits.open('%s/mergers/mergers_mpajhu_bpt.fits' % gzm_path) as f:
        data = f[1].data

    #sf_mergers = data[(data['bpt'] == 1) & (data['mass_ratio'] <= 3)]
    sf_mergers = data[(data['bpt'] == 1)]

    sc = ax.scatter(sf_mergers['MEDIAN_MASS'],sf_mergers['MEDIAN_SFR'], c=sf_mergers['mass_ratio'], edgecolor='none',s = 50, marker='.', cmap=matplotlib.cm.RdBu, vmin=1.,vmax=10.)

    ax.text(6.2,1.3,'Mergers', color='black',fontsize=20)

    # Plot the best linear fits

    #au,bu = plot_fits('Mergers',sf_mergers,ax,'red')
    a1,a0 = plot_fits('Star-forming galaxies',sfr_sample,ax,'black',lw=1,ls='-')

    # How many mergers fall above and below?

    diff = sf_mergers['MEDIAN_SFR'] - (a0 + a1*sf_mergers['MEDIAN_MASS'])

    # Fix same slope but different offset. What's the average difference between SF MS and mergers?

    mass,sfr,sfr_err = get_mass_sfr(sf_mergers)

    rms = []
    xarr = np.linspace(0,1,100)
    for x in xarr:
        rms.append(np.sqrt(np.sum((sfr - (a0 + x + a1*mass))**2)))

    offset = xarr[(np.abs(rms)).argmin()]
    uline = ax.plot(np.linspace(6,12,100),np.polyval([a1,a0+offset],np.linspace(6,12,100)),color='red',linestyle='--',linewidth=1)

    ax.text(6.2,0.9,'Offset = %.3f dex' % offset, color='black',fontsize=15)

    # Set the colorbars and labels

    box = ax.get_position()
    axColorbar = plt.axes([box.x0 + box.width * 1.02, box.y0, 0.01, box.height])
    cb = plt.colorbar(h[3],cax = axColorbar, orientation="vertical")
    cb.set_label(r'$N_\mathrm{star-forming\/galaxies}$' ,fontsize=16)

    axcb2 = plt.axes([0.75, 0.20, 0.03, 0.25]) 
    cb2 = plt.colorbar(sc,cax = axcb2, orientation="vertical",ticks=[1,3,5,10])
    cb2.set_label('Merger ratio',fontsize=14)

    fig.savefig('%s/ms_mergers.pdf' % fig_path, dpi=200)

    return None

def plot_ms_greenpeas(sfr_sample):

    # Plot

    fig = plt.figure(5,(10,8))
    fig.clf()

    fig.subplots_adjust(left=0.08,bottom=0.15,hspace=0,wspace=0)

    mass,sfr,sfr_err = get_mass_sfr(sfr_sample)
    mass_bins,sfr_bins = bins()
    h,xedges,yedges = np.histogram2d(mass,sfr,bins=(mass_bins,sfr_bins))

    # Plot star-forming galaxies

    ax = fig.add_subplot(111)
    h = ax.hist2d(mass,sfr,bins=50,cmap = cm.gray_r, norm=LogNorm())
    ax.set_xlim(6,11.5)
    ax.set_ylim(-4,2)
    ax.set_ylabel('log SFR '+r'$[M_\odot/\mathrm{yr}]$',fontsize=16)
    ax.set_xlabel('Stellar mass [log '+r'$\/M/M_\odot$]',fontsize=16)

    # Plot green peas

    with fits.open('%s/greenpeas.fits' % gzm_path) as f:
        data = f[1].data

    sc = ax.scatter(data['M_STELLAR'],np.log10(data['SFR']), color='green',s = 10, marker='o')

    ax.text(6.2,1.3,'Green peas', color='green')

    # Plot the best linear fits

    #au,bu = plot_fits('Mergers',sf_mergers,ax,'red')
    a1,a0 = plot_fits('Star-forming galaxies',sfr_sample,ax,'black',lw=1,ls='-')

    # Set the colorbars and labels

    box = ax.get_position()
    axColorbar = plt.axes([box.x0 + box.width * 1.02, box.y0, 0.01, box.height])
    cb = plt.colorbar(h[3],cax = axColorbar, orientation="vertical")
    cb.set_label(r'$N_\mathrm{star-forming\/galaxies}$' ,fontsize=16)

    fig.savefig('%s/ms_greenpeas.pdf' % fig_path, dpi=200)

    return None

def sigma_mstar(sfr_sample):

    '''
    Test whether populations are likely to be consistent by plotting dispersion as function of M_star for bins of M_star
    Overplot for different populations
    '''

    mass,sfr,sfr_err = get_mass_sfr(sfr_sample)
    mass_bins,sfr_bins = bins(mass_max=11.5,nbins=15)
    deltamass = mass_bins[1] - mass_bins[0]

    fig = plt.figure(6,(10,8))
    fig.clf()

    # Bars
    ax = fig.add_subplot(223)

    sigma_sfr = []
    sigma_sfr_err = []
    for mb in mass_bins:
        idx = (mass > (mb-deltamass)) & (mass <= (mb+deltamass))
        sigma_sfr.append(np.std(sfr[idx]))
        try:
            sigma_sfr_err.append(1./np.sum(idx))
        except ZeroDivisionError:
            sigma_sfr_err.append(0.)

    ax.errorbar(mass_bins,sigma_sfr,yerr=sigma_sfr_err,fmt='o',color='black',capsize=0)

    notedgeon = (sfr_sample['t01_smooth_or_features_a02_features_or_disk_debiased'] > 0.430) & (sfr_sample['t02_edgeon_a05_no_debiased'] > 0.715) & (sfr_sample['t02_edgeon_a05_no_weight'] >= 20)
    barred = sfr_sample[notedgeon & (sfr_sample['t03_bar_a06_bar_debiased'] >= 0.4)] 
    unbarred = sfr_sample[notedgeon & (sfr_sample['t03_bar_a06_bar_debiased'] < 0.4)] 

    bar_data = (barred,unbarred)
    bar_text = ('Barred','Unbarred')
    color = ('blue','red')

    for idx, (b,c,t) in enumerate(zip(bar_data,color,bar_text)):

        sigma_sfr,sigma_sfr_err,ngals = [],[],[]
        for mb in mass_bins:
            idx = (b['MEDIAN_MASS'] > (mb-deltamass)) & (b['MEDIAN_MASS'] <= (mb+deltamass))
            sigma_sfr.append(np.std(b['MEDIAN_SFR'][idx]))
            try:
                sigma_sfr_err.append(1./np.sum(idx))
            except ZeroDivisionError:
                sigma_sfr_err.append(0.)
            ngals.append(np.sum(idx))

        gtr10 = (np.array(ngals) >= 10)
        ax.errorbar(mass_bins[gtr10],np.array(sigma_sfr)[gtr10],yerr=np.array(sigma_sfr_err)[gtr10],color=c,capsize=0)

    # Final plot labels and ranges
    ax.set_xlim(6,11.5)
    ax.set_ylim(0,1.2)
    ax.set_ylabel(r'$\sigma_{SFR}~[\log M_\odot/\mathrm{yr}]$',fontsize=16)
    ax.set_xlabel('Stellar mass [log '+r'$\/M/M_\odot$]',fontsize=16)
    ax.set_title('Bar/no bar')

    # Arm number
    ax = fig.add_subplot(221)

    sigma_sfr = []
    sigma_sfr_err = []
    for mb in mass_bins:
        idx = (mass > (mb-deltamass)) & (mass <= (mb+deltamass))
        sigma_sfr.append(np.std(sfr[idx]))
        try:
            sigma_sfr_err.append(1./np.sum(idx))
        except ZeroDivisionError:
            sigma_sfr_err.append(0.)

    ax.errorbar(mass_bins,sigma_sfr,yerr=sigma_sfr_err,fmt='o',color='black',capsize=0)

    arm_tasks = ('a31_1','a32_2','a33_3','a34_4','a36_more_than_4','a37_cant_tell')
    arm_label = ('1','2','3','4','5+','??')
    colors = ('red','orange','yellow','green','blue','purple')
    for idx, (a,c,al) in enumerate(zip(arm_tasks,colors,arm_label)):

        spiral = (sfr_sample['t01_smooth_or_features_a02_features_or_disk_debiased'] > 0.430) & (sfr_sample['t02_edgeon_a05_no_debiased'] > 0.715) & (sfr_sample['t04_spiral_a08_spiral_weight'] >= 20) & (sfr_sample['t04_spiral_a08_spiral_debiased'] > 0.619)
        n1 = sfr_sample[spiral & (sfr_sample['t11_arms_number_%s_flag' % a] == 1)] 

        sigma_sfr,sigma_sfr_err,ngals = [],[],[]
        for mb in mass_bins:
            idx = (n1['MEDIAN_MASS'] > (mb-deltamass)) & (n1['MEDIAN_MASS'] <= (mb+deltamass))
            sigma_sfr.append(np.std(n1['MEDIAN_SFR'][idx]))
            try:
                sigma_sfr_err.append(1./np.sum(idx))
            except ZeroDivisionError:
                sigma_sfr_err.append(0.)
            ngals.append(np.sum(idx))

        gtr10 = (np.array(ngals) >= 10)
        ax.errorbar(mass_bins[gtr10],np.array(sigma_sfr)[gtr10],yerr=np.zeros_like(sigma_sfr)[gtr10],color=c,capsize=0)

    # Final plot labels and ranges
    ax.set_xlim(6,11.5)
    ax.set_ylim(0,1.2)
    ax.set_ylabel(r'$\sigma_{SFR}~[\log M_\odot/\mathrm{yr}]$',fontsize=16)
    ax.set_xlabel('Stellar mass [log '+r'$\/M/M_\odot$]',fontsize=16)
    ax.set_title('Arms number')

    # Arm winding
    ax = fig.add_subplot(222)

    sigma_sfr = []
    sigma_sfr_err = []
    for mb in mass_bins:
        idx = (mass > (mb-deltamass)) & (mass <= (mb+deltamass))
        sigma_sfr.append(np.std(sfr[idx]))
        try:
            sigma_sfr_err.append(1./np.sum(idx))
        except ZeroDivisionError:
            sigma_sfr_err.append(0.)

    ax.errorbar(mass_bins,sigma_sfr,yerr=sigma_sfr_err,fmt='o',color='black',capsize=0)

    arm_tasks = ('a28_tight','a29_medium','a30_loose')
    colors = ('red','green','blue')
    for idx, (a,c) in enumerate(zip(arm_tasks,colors)):

        spiral = (sfr_sample['t01_smooth_or_features_a02_features_or_disk_debiased'] > 0.430) & (sfr_sample['t02_edgeon_a05_no_debiased'] > 0.715) & (sfr_sample['t04_spiral_a08_spiral_weight'] >= 20) & (sfr_sample['t04_spiral_a08_spiral_debiased'] > 0.619)
        n1 = sfr_sample[spiral & (sfr_sample['t10_arms_winding_%s_flag' % a] == 1)] 

        sigma_sfr,sigma_sfr_err,ngals = [],[],[]
        for mb in mass_bins:
            idx = (n1['MEDIAN_MASS'] > (mb-deltamass)) & (n1['MEDIAN_MASS'] <= (mb+deltamass))
            sigma_sfr.append(np.std(n1['MEDIAN_SFR'][idx]))
            try:
                sigma_sfr_err.append(1./np.sum(idx))
            except ZeroDivisionError:
                sigma_sfr_err.append(0.)
            ngals.append(np.sum(idx))

        gtr10 = (np.array(ngals) >= 10)
        ax.errorbar(mass_bins[gtr10],np.array(sigma_sfr)[gtr10],yerr=np.array(sigma_sfr_err)[gtr10],color=c,capsize=0)

    # Final plot labels and ranges
    ax.set_xlim(6,11.5)
    ax.set_ylim(0,1.2)
    ax.set_ylabel(r'$\sigma_{SFR}~[\log M_\odot/\mathrm{yr}]$',fontsize=16)
    ax.set_xlabel('Stellar mass [log '+r'$\/M/M_\odot$]',fontsize=16)
    ax.set_title('Arms winding')

    # Mergers
    ax = fig.add_subplot(224)

    sigma_sfr = []
    sigma_sfr_err = []
    for mb in mass_bins:
        idx = (mass > (mb-deltamass)) & (mass <= (mb+deltamass))
        sigma_sfr.append(np.std(sfr[idx]))
        try:
            sigma_sfr_err.append(1./np.sum(idx))
        except ZeroDivisionError:
            sigma_sfr_err.append(0.)

    ax.errorbar(mass_bins,sigma_sfr,yerr=sigma_sfr_err,fmt='o',color='black',capsize=0)

    with fits.open('%s/mergers/mergers_mpajhu_bpt.fits' % gzm_path) as f:
        data = f[1].data

    sf_mergers = data[(data['bpt'] == 1)]

    sigma_sfr,sigma_sfr_err,ngals = [],[],[]
    for mb in mass_bins:
        idx = (sf_mergers['MEDIAN_MASS'] > (mb-deltamass)) & (sf_mergers['MEDIAN_MASS'] <= (mb+deltamass))
        sigma_sfr.append(np.std(sf_mergers['MEDIAN_SFR'][idx]))
        try:
            sigma_sfr_err.append(1./np.sum(idx))
        except ZeroDivisionError:
            sigma_sfr_err.append(0.)
        ngals.append(np.sum(idx))

    gtr10 = (np.array(ngals) >= 10)
    ax.errorbar(mass_bins[gtr10],np.array(sigma_sfr)[gtr10],yerr=np.array(sigma_sfr_err)[gtr10],color='red',capsize=0)

    # Final plot labels and ranges
    ax.set_xlim(6,11.5)
    ax.set_ylim(0,1.2)
    ax.set_ylabel(r'$\sigma_{SFR}~[\log M_\odot/\mathrm{yr}]$',fontsize=16)
    ax.set_xlabel('Stellar mass [log '+r'$\/M/M_\odot$]',fontsize=16)
    ax.set_title('Mergers')

    fig.set_tight_layout(True)
    fig.savefig('%s/sigma_mstar.pdf' % fig_path, dpi=200)

    return None

def plot_ms_merger_fraction(sfr_sample):

    # Plot

    fig = plt.figure(7,(10,8))
    fig.clf()

    fig.subplots_adjust(left=0.08,bottom=0.15,right=0.9,hspace=0,wspace=0)

    mass,sfr,sfr_err = get_mass_sfr(sfr_sample)
    mass_bins,sfr_bins = bins(nbins=30)
    h,xedges,yedges = np.histogram2d(mass,sfr,bins=(mass_bins,sfr_bins))

    # Plot star-forming galaxies

    ax = fig.add_subplot(111)
    levels=10**(np.linspace(0,5,15))
    CS = ax.contour(mass_bins[1:],sfr_bins[1:],h.T,levels,colors='black')
    ax.set_xlim(6,11.5)
    ax.set_ylim(-4,2)
    ax.set_ylabel('log SFR '+r'$[M_\odot/\mathrm{yr}]$',fontsize=16)
    ax.set_xlabel('Stellar mass [log '+r'$\/M/M_\odot$]',fontsize=16)

    # Plot mergers data

    with fits.open('%s/mergers/mergers_mpajhu_bpt.fits' % gzm_path) as f:
        data = f[1].data

    #sf_mergers = data[(data['bpt'] == 1) & (data['mass_ratio'] <= 3)]
    sf_mergers = data[(data['bpt'] == 1)]

    #sc = ax.scatter(sf_mergers['MEDIAN_MASS'],sf_mergers['MEDIAN_SFR'], c=sf_mergers['mass_ratio'], edgecolor='none',s = 50, marker='.', cmap=matplotlib.cm.RdBu, vmin=1.,vmax=10.)
    hm,xm,ym = np.histogram2d(sf_mergers['MEDIAN_MASS'],sf_mergers['MEDIAN_SFR'],bins=(mass_bins,sfr_bins))
    mf = hm / h
    im = ax.imshow(mf.T, interpolation='nearest', origin='lower',extent=(mass_bins[0],mass_bins[-1],sfr_bins[0],sfr_bins[-1]),vmin=0.,vmax=1.)
    cb = plt.colorbar(im)

    ax.text(6.2,1.3,'Merger fraction', color='black',fontsize=20)

    # Plot the best linear fits

    #au,bu = plot_fits('Mergers',sf_mergers,ax,'red')
    a1,a0 = plot_fits('Star-forming galaxies',sfr_sample,ax,'black',lw=3,ls='-')

    # How many mergers fall above and below?

    diff = sf_mergers['MEDIAN_SFR'] - (a0 + a1*sf_mergers['MEDIAN_MASS'])

    # Fix same slope but different offset. What's the average difference between SF MS and mergers?

    mass,sfr,sfr_err = get_mass_sfr(sf_mergers)

    rms = []
    xarr = np.linspace(0,1,100)
    for x in xarr:
        rms.append(np.sqrt(np.sum((sfr - (a0 + x + a1*mass))**2)))

    offset = xarr[(np.abs(rms)).argmin()]
    uline = ax.plot(np.linspace(6,12,100),np.polyval([a1,a0+offset],np.linspace(6,12,100)),color='red',linestyle='--',linewidth=1)

    ax.text(6.2,0.9,'Offset = %.3f dex' % offset, color='black',fontsize=15)

    fig.savefig('%s/ms_merger_fraction.pdf' % fig_path, dpi=200)

    return None

def plot_ms_mergers_both(sfr_sample):

    #---------------------------------
    # Merger counts
    #---------------------------------

    fig = plt.figure(8,(14,7))
    fig.clf()

    #fig.subplots_adjust(left=0.08,bottom=0.15,right=0.90,hspace=0,wspace=0.05)

    mass,sfr,sfr_err = get_mass_sfr(sfr_sample)

    # Plot star-forming galaxies

    ax1 = fig.add_axes([0.07,0.10,0.42,0.85])
    h = ax1.hist2d(mass,sfr,bins=50,cmap = cm.gray_r, norm=LogNorm())
    ax1.set_xlim(6,11.5)
    ax1.set_ylim(-4,2)
    ax1.set_ylabel('log SFR '+r'$[M_\odot/\mathrm{yr}]$',fontsize=16)
    ax1.set_xlabel('Stellar mass [log '+r'$\/M/M_\odot$]',fontsize=16)

    # Plot mergers data

    with fits.open('%s/mergers/mergers_mpajhu_bpt.fits' % gzm_path) as f:
        data = f[1].data

    sf_mergers = data[(data['bpt'] == 1)]

    sc = ax1.scatter(sf_mergers['MEDIAN_MASS'],sf_mergers['MEDIAN_SFR'], c=sf_mergers['mass_ratio'], edgecolor='none',s = 50, marker='.', cmap=matplotlib.cm.RdBu, vmin=1.,vmax=10.)

    ax1.text(6.2,1.3,'Mergers', color='black',fontsize=20)

    # Plot the best linear fits

    a1,a0 = plot_fits('Star-forming galaxies',sfr_sample,ax1,'black',lw=3,ls='-')

    # Fix same slope but different offset. 

    mass_mergers,sfr_mergers,sfr_err_mergers = get_mass_sfr(sf_mergers)

    rms = []
    xarr = np.linspace(0,1,100)
    for x in xarr:
        rms.append(np.sqrt(np.sum((sfr_mergers - (a0 + x + a1*mass_mergers))**2)))

    offset = xarr[(np.abs(rms)).argmin()]
    uline = ax1.plot(np.linspace(6,12,100),np.polyval([a1,a0+offset],np.linspace(6,12,100)),color='red',linestyle='--',linewidth=3)

    ax1.text(6.2,0.9,'Offset = %.3f dex' % offset, color='black',fontsize=15)

    # Set the colorbars and labels

    axcb1 = plt.axes([0.40, 0.20, 0.03, 0.25]) 
    cb1 = plt.colorbar(sc,cax = axcb1, orientation="vertical",ticks=[1,3,5,10])
    cb1.set_label('Mass ratio',fontsize=14)

    ax1.xaxis.labelpad = 20
    #---------------------------------
    # Merger fraction
    #---------------------------------

    mass_bins,sfr_bins = bins(nbins=30)
    h,xedges,yedges = np.histogram2d(mass,sfr,bins=(mass_bins,sfr_bins))

    # Plot star-forming galaxies

    ax2 = fig.add_axes([0.460,0.10,0.45,0.85])
    levels=10**(np.linspace(0,5,15))
    CS = ax2.contour(mass_bins[1:],sfr_bins[1:],h.T,levels,colors='black')
    ax2.set_xlim(6,11.5)
    ax2.set_ylim(-4,2)
    ax2.set_xlabel('Stellar mass [log '+r'$\/M/M_\odot$]',fontsize=16)

    hm,xm,ym = np.histogram2d(sf_mergers['MEDIAN_MASS'],sf_mergers['MEDIAN_SFR'],bins=(mass_bins,sfr_bins))
    mf = hm / h
    im = ax2.imshow(mf.T, interpolation='nearest', origin='lower',extent=(mass_bins[0],mass_bins[-1],sfr_bins[0],sfr_bins[-1]),vmin=0.,vmax=1.)

    axcb2 = plt.axes([0.90, 0.10, 0.02, 0.85]) 
    cb2 = plt.colorbar(im,cax = axcb2, orientation="vertical")
    cb2.set_label('Merger fraction',fontsize=16)

    ax2.text(6.2,1.3,'Merger fraction', color='black',fontsize=20)

    ax2.set_yticklabels([])

    # Plot the best linear fits

    a1,a0 = plot_fits('Star-forming galaxies',sfr_sample,ax2,'black',lw=3,ls='-')
    uline = ax2.plot(np.linspace(6,12,100),np.polyval([a1,a0+offset],np.linspace(6,12,100)),color='red',linestyle='--',linewidth=3)

    ax2.xaxis.labelpad = 20

    #fig.set_tight_layout(True)
    fig.savefig('%s/ms_mergers_both.pdf' % fig_path, dpi=200)

    return None

def fracdev(sfr_sample):

    # Find the fracdev distribution for all of the various spiral classes, per Ivy Wong's suggestion

    # Contained in the original gz2_sample table, and thus in the joined mpajhu_gz2.fits table.

    # Overall sample, plus 6 multiplicity, 3 winding, 2 bars, merger = 12

    # Good opportunity to take the plurality answer

    fig = plt.figure(9,(15,10))
    fig.clf()

    fig.subplots_adjust(left=0.08,bottom=0.15,right=0.9,hspace=0.02,wspace=0.02)

    spiral = (sfr_sample['t01_smooth_or_features_a02_features_or_disk_debiased'] > 0.430) & (sfr_sample['t02_edgeon_a05_no_debiased'] > 0.715) & (sfr_sample['t04_spiral_a08_spiral_weight'] >= 20) & (sfr_sample['t04_spiral_a08_spiral_debiased'] > 0.619)

    # Find plurality answer for multiplicity question

    an_1 = sfr_sample[spiral & \
                       (sfr_sample['t11_arms_number_a31_1_debiased'] >= sfr_sample['t11_arms_number_a32_2_debiased']) & \
                       (sfr_sample['t11_arms_number_a31_1_debiased'] >= sfr_sample['t11_arms_number_a33_3_debiased']) & \
                       (sfr_sample['t11_arms_number_a31_1_debiased'] >= sfr_sample['t11_arms_number_a34_4_debiased']) & \
                       (sfr_sample['t11_arms_number_a31_1_debiased'] >= sfr_sample['t11_arms_number_a36_more_than_4_debiased']) & \
                       (sfr_sample['t11_arms_number_a31_1_debiased'] >= sfr_sample['t11_arms_number_a37_cant_tell_debiased']) ]

    an_2 = sfr_sample[spiral & \
                       (sfr_sample['t11_arms_number_a32_2_debiased'] >= sfr_sample['t11_arms_number_a31_1_debiased']) & \
                       (sfr_sample['t11_arms_number_a32_2_debiased'] >= sfr_sample['t11_arms_number_a33_3_debiased']) & \
                       (sfr_sample['t11_arms_number_a32_2_debiased'] >= sfr_sample['t11_arms_number_a34_4_debiased']) & \
                       (sfr_sample['t11_arms_number_a32_2_debiased'] >= sfr_sample['t11_arms_number_a36_more_than_4_debiased']) & \
                       (sfr_sample['t11_arms_number_a32_2_debiased'] >= sfr_sample['t11_arms_number_a37_cant_tell_debiased']) ]

    an_3 = sfr_sample[spiral & \
                       (sfr_sample['t11_arms_number_a33_3_debiased'] >= sfr_sample['t11_arms_number_a32_2_debiased']) & \
                       (sfr_sample['t11_arms_number_a33_3_debiased'] >= sfr_sample['t11_arms_number_a31_1_debiased']) & \
                       (sfr_sample['t11_arms_number_a33_3_debiased'] >= sfr_sample['t11_arms_number_a34_4_debiased']) & \
                       (sfr_sample['t11_arms_number_a33_3_debiased'] >= sfr_sample['t11_arms_number_a36_more_than_4_debiased']) & \
                       (sfr_sample['t11_arms_number_a33_3_debiased'] >= sfr_sample['t11_arms_number_a37_cant_tell_debiased']) ]

    an_4 = sfr_sample[spiral & \
                       (sfr_sample['t11_arms_number_a34_4_debiased'] >= sfr_sample['t11_arms_number_a32_2_debiased']) & \
                       (sfr_sample['t11_arms_number_a34_4_debiased'] >= sfr_sample['t11_arms_number_a33_3_debiased']) & \
                       (sfr_sample['t11_arms_number_a34_4_debiased'] >= sfr_sample['t11_arms_number_a31_1_debiased']) & \
                       (sfr_sample['t11_arms_number_a34_4_debiased'] >= sfr_sample['t11_arms_number_a36_more_than_4_debiased']) & \
                       (sfr_sample['t11_arms_number_a34_4_debiased'] >= sfr_sample['t11_arms_number_a37_cant_tell_debiased']) ]

    an_5 = sfr_sample[spiral & \
                       (sfr_sample['t11_arms_number_a36_more_than_4_debiased'] >= sfr_sample['t11_arms_number_a32_2_debiased']) & \
                       (sfr_sample['t11_arms_number_a36_more_than_4_debiased'] >= sfr_sample['t11_arms_number_a33_3_debiased']) & \
                       (sfr_sample['t11_arms_number_a36_more_than_4_debiased'] >= sfr_sample['t11_arms_number_a34_4_debiased']) & \
                       (sfr_sample['t11_arms_number_a36_more_than_4_debiased'] >= sfr_sample['t11_arms_number_a31_1_debiased']) & \
                       (sfr_sample['t11_arms_number_a36_more_than_4_debiased'] >= sfr_sample['t11_arms_number_a37_cant_tell_debiased']) ]

    an_x = sfr_sample[spiral & \
                       (sfr_sample['t11_arms_number_a37_cant_tell_debiased'] >= sfr_sample['t11_arms_number_a32_2_debiased']) & \
                       (sfr_sample['t11_arms_number_a37_cant_tell_debiased'] >= sfr_sample['t11_arms_number_a33_3_debiased']) & \
                       (sfr_sample['t11_arms_number_a37_cant_tell_debiased'] >= sfr_sample['t11_arms_number_a34_4_debiased']) & \
                       (sfr_sample['t11_arms_number_a37_cant_tell_debiased'] >= sfr_sample['t11_arms_number_a36_more_than_4_debiased']) & \
                       (sfr_sample['t11_arms_number_a37_cant_tell_debiased'] >= sfr_sample['t11_arms_number_a31_1_debiased']) ]

    aw_t = sfr_sample[spiral & \
                       (sfr_sample['t10_arms_winding_a28_tight_debiased'] >= sfr_sample['t10_arms_winding_a29_medium_debiased']) & \
                       (sfr_sample['t10_arms_winding_a28_tight_debiased'] >= sfr_sample['t10_arms_winding_a30_loose_debiased'])]

    aw_m = sfr_sample[spiral & \
                       (sfr_sample['t10_arms_winding_a29_medium_debiased'] >= sfr_sample['t10_arms_winding_a28_tight_debiased']) & \
                       (sfr_sample['t10_arms_winding_a29_medium_debiased'] >= sfr_sample['t10_arms_winding_a30_loose_debiased'])]

    aw_l = sfr_sample[spiral & \
                       (sfr_sample['t10_arms_winding_a30_loose_debiased'] >= sfr_sample['t10_arms_winding_a29_medium_debiased']) & \
                       (sfr_sample['t10_arms_winding_a30_loose_debiased'] >= sfr_sample['t10_arms_winding_a28_tight_debiased'])]

    aw_l = sfr_sample[spiral & \
                       (sfr_sample['t10_arms_winding_a30_loose_debiased'] >= sfr_sample['t10_arms_winding_a29_medium_debiased']) & \
                       (sfr_sample['t10_arms_winding_a30_loose_debiased'] >= sfr_sample['t10_arms_winding_a28_tight_debiased'])]


    notedgeon = (sfr_sample['t01_smooth_or_features_a02_features_or_disk_debiased'] > 0.430) & (sfr_sample['t02_edgeon_a05_no_debiased'] > 0.715) & (sfr_sample['t02_edgeon_a05_no_weight'] >= 20)

    barred = sfr_sample[notedgeon & (sfr_sample['t03_bar_a06_bar_debiased'] >= 0.5)] 
    unbarred = sfr_sample[notedgeon & (sfr_sample['t03_bar_a06_bar_debiased'] < 0.5)] 

    with fits.open('%s/mergers/mergers_fracdev.fits' % gzm_path) as f:
        data = f[1].data

    sf_mergers = data[(data['bpt'] == 1)]

    axc = fig.add_subplot(111)    # The big subplot
    axc.spines['top'].set_color('none')
    axc.spines['bottom'].set_color('none')
    axc.spines['left'].set_color('none')
    axc.spines['right'].set_color('none')
    axc.tick_params(labelcolor='none', top='off', bottom='off', left='off', right='off')
    axc.set_xlabel(r'$f_{DeV}$ (r-band)',labelpad=10,fontsize=20)
    axc.set_ylabel('Normalized count',labelpad=20,fontsize=20)

    axc.set_title('frac deV distribution for GZ2 galaxies',fontsize=25)

    ax = fig.add_subplot(341)
    n, bins, patches = ax.hist(sfr_sample['FRACDEV_R'], 25, histtype='stepfilled', weights=np.ones_like(sfr_sample['FRACDEV_R'])/len(sfr_sample), facecolor='gray', edgecolor='black', alpha=0.75)
    ax.get_xaxis().set_ticks([])
    ax.get_yaxis().set_ticks([0.0,0.10,0.20,0.30])
    n_sub, bins_sub, patches_sub = ax.hist(an_1['FRACDEV_R'], 25, histtype='step', weights=np.ones_like(an_1['FRACDEV_R'])/len(an_1), edgecolor=an_colors[0], alpha=1., lw=3)
    ax.text(0.95,0.28,'1 arm',fontsize=12,ha='right')

    ax = fig.add_subplot(342)
    n, bins, patches = ax.hist(sfr_sample['FRACDEV_R'], 25, histtype='stepfilled', weights=np.ones_like(sfr_sample['FRACDEV_R'])/len(sfr_sample), facecolor='gray', edgecolor='black', alpha=0.75)
    ax.get_xaxis().set_ticks([])
    ax.get_yaxis().set_ticks([])
    n_sub, bins_sub, patches_sub = ax.hist(an_2['FRACDEV_R'], 25, histtype='step', weights=np.ones_like(an_2['FRACDEV_R'])/len(an_2), edgecolor=an_colors[1], alpha=1., lw=3)
    ax.text(0.95,0.28,'2 arms',fontsize=12,ha='right')

    ax = fig.add_subplot(343)
    n, bins, patches = ax.hist(sfr_sample['FRACDEV_R'], 25, histtype='stepfilled', weights=np.ones_like(sfr_sample['FRACDEV_R'])/len(sfr_sample), facecolor='gray', edgecolor='black', alpha=0.75)
    ax.get_xaxis().set_ticks([])
    ax.get_yaxis().set_ticks([])
    n_sub, bins_sub, patches_sub = ax.hist(an_3['FRACDEV_R'], 25, histtype='step', weights=np.ones_like(an_3['FRACDEV_R'])/len(an_3), edgecolor=an_colors[2], alpha=1., lw=3)
    ax.text(0.95,0.28,'3 arms',fontsize=12,ha='right')

    ax = fig.add_subplot(344)
    n, bins, patches = ax.hist(sfr_sample['FRACDEV_R'], 25, histtype='stepfilled', weights=np.ones_like(sfr_sample['FRACDEV_R'])/len(sfr_sample), facecolor='gray', edgecolor='black', alpha=0.75)
    ax.get_xaxis().set_ticks([])
    ax.get_yaxis().set_ticks([])
    n_sub, bins_sub, patches_sub = ax.hist(an_4['FRACDEV_R'], 25, histtype='step', weights=np.ones_like(an_4['FRACDEV_R'])/len(an_4), edgecolor=an_colors[3], alpha=1., lw=3)
    ax.text(0.95,0.28,'4 arms',fontsize=12,ha='right')

    ax = fig.add_subplot(345)
    n, bins, patches = ax.hist(sfr_sample['FRACDEV_R'], 25, histtype='stepfilled', weights=np.ones_like(sfr_sample['FRACDEV_R'])/len(sfr_sample), facecolor='gray', edgecolor='black', alpha=0.75)
    ax.get_xaxis().set_ticks([])
    ax.get_yaxis().set_ticks([0.0,0.10,0.20,0.30])
    n_sub, bins_sub, patches_sub = ax.hist(an_5['FRACDEV_R'], 25, histtype='step', weights=np.ones_like(an_5['FRACDEV_R'])/len(an_5), edgecolor=an_colors[4], alpha=1., lw=3)
    ax.text(0.95,0.28,'5+ arms',fontsize=12,ha='right')

    ax = fig.add_subplot(346)
    n, bins, patches = ax.hist(sfr_sample['FRACDEV_R'], 25, histtype='stepfilled', weights=np.ones_like(sfr_sample['FRACDEV_R'])/len(sfr_sample), facecolor='gray', edgecolor='black', alpha=0.75)
    ax.get_xaxis().set_ticks([])
    ax.get_yaxis().set_ticks([])
    n_sub, bins_sub, patches_sub = ax.hist(an_x['FRACDEV_R'], 25, histtype='step', weights=np.ones_like(an_x['FRACDEV_R'])/len(an_x), edgecolor=an_colors[5], alpha=1., lw=3)
    ax.text(0.95,0.28,'?? arms',fontsize=12,ha='right')

    ax = fig.add_subplot(347)
    n, bins, patches = ax.hist(sfr_sample['FRACDEV_R'], 25, histtype='stepfilled', weights=np.ones_like(sfr_sample['FRACDEV_R'])/len(sfr_sample), facecolor='gray', edgecolor='black', alpha=0.75)
    ax.get_xaxis().set_ticks([])
    ax.get_yaxis().set_ticks([])
    n_sub, bins_sub, patches_sub = ax.hist(aw_t['FRACDEV_R'], 25, histtype='step', weights=np.ones_like(aw_t['FRACDEV_R'])/len(aw_t), edgecolor=aw_colors[0], alpha=1., lw=3)
    ax.text(0.95,0.28,'Tight arms',fontsize=12,ha='right')

    ax = fig.add_subplot(348)
    n, bins, patches = ax.hist(sfr_sample['FRACDEV_R'], 25, histtype='stepfilled', weights=np.ones_like(sfr_sample['FRACDEV_R'])/len(sfr_sample), facecolor='gray', edgecolor='black', alpha=0.75)
    ax.get_xaxis().set_ticks([])
    ax.get_yaxis().set_ticks([])
    n_sub, bins_sub, patches_sub = ax.hist(aw_m['FRACDEV_R'], 25, histtype='step', weights=np.ones_like(aw_m['FRACDEV_R'])/len(aw_m), edgecolor=aw_colors[1], alpha=1., lw=3)
    ax.text(0.95,0.28,'Medium arms',fontsize=12,ha='right')

    ax = fig.add_subplot(349)
    n, bins, patches = ax.hist(sfr_sample['FRACDEV_R'], 25, histtype='stepfilled', weights=np.ones_like(sfr_sample['FRACDEV_R'])/len(sfr_sample), facecolor='gray', edgecolor='black', alpha=0.75)
    ax.get_xaxis().set_ticks([0.0,0.2,0.4,0.6,0.8])
    ax.get_yaxis().set_ticks([0.0,0.10,0.20,0.30])
    n_sub, bins_sub, patches_sub = ax.hist(aw_l['FRACDEV_R'], 25, histtype='step', weights=np.ones_like(aw_l['FRACDEV_R'])/len(aw_l), edgecolor=aw_colors[2], alpha=1., lw=3)
    ax.text(0.95,0.28,'Loose arms',fontsize=12,ha='right')

    ax = fig.add_subplot(3,4,10)
    n, bins, patches = ax.hist(sfr_sample['FRACDEV_R'], 25, histtype='stepfilled', weights=np.ones_like(sfr_sample['FRACDEV_R'])/len(sfr_sample), facecolor='gray', edgecolor='black', alpha=0.75)
    ax.get_xaxis().set_ticks([0.0,0.2,0.4,0.6,0.8])
    ax.get_yaxis().set_ticks([])
    n_sub, bins_sub, patches_sub = ax.hist(unbarred['FRACDEV_R'], 25, histtype='step', weights=np.ones_like(unbarred['FRACDEV_R'])/len(unbarred), edgecolor='red', alpha=1., lw=3)
    ax.text(0.95,0.28,'Unbarred',fontsize=12,ha='right')

    ax = fig.add_subplot(3,4,11)
    n, bins, patches = ax.hist(sfr_sample['FRACDEV_R'], 25, histtype='stepfilled', weights=np.ones_like(sfr_sample['FRACDEV_R'])/len(sfr_sample), facecolor='gray', edgecolor='black', alpha=0.75)
    ax.get_xaxis().set_ticks([0.0,0.2,0.4,0.6,0.8])
    ax.get_yaxis().set_ticks([])
    n_sub, bins_sub, patches_sub = ax.hist(barred['FRACDEV_R'], 25, histtype='step', weights=np.ones_like(barred['FRACDEV_R'])/len(barred), edgecolor='blue', alpha=1., lw=3)
    ax.text(0.95,0.28,'Barred',fontsize=12,ha='right')

    ax = fig.add_subplot(3,4,12)
    n, bins, patches = ax.hist(sfr_sample['FRACDEV_R'], 25, histtype='stepfilled', weights=np.ones_like(sfr_sample['FRACDEV_R'])/len(sfr_sample), facecolor='gray', edgecolor='black', alpha=0.75)
    ax.get_yaxis().set_ticks([])
    n_sub, bins_sub, patches_sub = ax.hist(sf_mergers['FRACDEV_R'], 25, histtype='step', weights=np.ones_like(sf_mergers['FRACDEV_R'])/len(sf_mergers), edgecolor='red', alpha=1., lw=3)
    ax.text(0.95,0.28,'Mergers',fontsize=12,ha='right')

    plt.show()

    fig.savefig('%s/fracdev_hist.pdf' % fig_path, dpi=200)

    return None

def fracdev_cdf(sfr_sample):

    # Find the CDF of the fracdev distribution for all of the various spiral classes, per Ivy Wong's suggestion

    fig = plt.figure(10,(10,10))
    fig.clf()

    fig.subplots_adjust(left=0.08,bottom=0.15,right=0.9,hspace=0.02,wspace=0.02)

    spiral = (sfr_sample['t01_smooth_or_features_a02_features_or_disk_debiased'] > 0.430) & (sfr_sample['t02_edgeon_a05_no_debiased'] > 0.715) & (sfr_sample['t04_spiral_a08_spiral_weight'] >= 20) & (sfr_sample['t04_spiral_a08_spiral_debiased'] > 0.619)

    # Find plurality answer for multiplicity question

    an_1 = sfr_sample[spiral & \
                       (sfr_sample['t11_arms_number_a31_1_debiased'] >= sfr_sample['t11_arms_number_a32_2_debiased']) & \
                       (sfr_sample['t11_arms_number_a31_1_debiased'] >= sfr_sample['t11_arms_number_a33_3_debiased']) & \
                       (sfr_sample['t11_arms_number_a31_1_debiased'] >= sfr_sample['t11_arms_number_a34_4_debiased']) & \
                       (sfr_sample['t11_arms_number_a31_1_debiased'] >= sfr_sample['t11_arms_number_a36_more_than_4_debiased']) & \
                       (sfr_sample['t11_arms_number_a31_1_debiased'] >= sfr_sample['t11_arms_number_a37_cant_tell_debiased']) ]

    an_2 = sfr_sample[spiral & \
                       (sfr_sample['t11_arms_number_a32_2_debiased'] >= sfr_sample['t11_arms_number_a31_1_debiased']) & \
                       (sfr_sample['t11_arms_number_a32_2_debiased'] >= sfr_sample['t11_arms_number_a33_3_debiased']) & \
                       (sfr_sample['t11_arms_number_a32_2_debiased'] >= sfr_sample['t11_arms_number_a34_4_debiased']) & \
                       (sfr_sample['t11_arms_number_a32_2_debiased'] >= sfr_sample['t11_arms_number_a36_more_than_4_debiased']) & \
                       (sfr_sample['t11_arms_number_a32_2_debiased'] >= sfr_sample['t11_arms_number_a37_cant_tell_debiased']) ]

    an_3 = sfr_sample[spiral & \
                       (sfr_sample['t11_arms_number_a33_3_debiased'] >= sfr_sample['t11_arms_number_a32_2_debiased']) & \
                       (sfr_sample['t11_arms_number_a33_3_debiased'] >= sfr_sample['t11_arms_number_a31_1_debiased']) & \
                       (sfr_sample['t11_arms_number_a33_3_debiased'] >= sfr_sample['t11_arms_number_a34_4_debiased']) & \
                       (sfr_sample['t11_arms_number_a33_3_debiased'] >= sfr_sample['t11_arms_number_a36_more_than_4_debiased']) & \
                       (sfr_sample['t11_arms_number_a33_3_debiased'] >= sfr_sample['t11_arms_number_a37_cant_tell_debiased']) ]

    an_4 = sfr_sample[spiral & \
                       (sfr_sample['t11_arms_number_a34_4_debiased'] >= sfr_sample['t11_arms_number_a32_2_debiased']) & \
                       (sfr_sample['t11_arms_number_a34_4_debiased'] >= sfr_sample['t11_arms_number_a33_3_debiased']) & \
                       (sfr_sample['t11_arms_number_a34_4_debiased'] >= sfr_sample['t11_arms_number_a31_1_debiased']) & \
                       (sfr_sample['t11_arms_number_a34_4_debiased'] >= sfr_sample['t11_arms_number_a36_more_than_4_debiased']) & \
                       (sfr_sample['t11_arms_number_a34_4_debiased'] >= sfr_sample['t11_arms_number_a37_cant_tell_debiased']) ]

    an_5 = sfr_sample[spiral & \
                       (sfr_sample['t11_arms_number_a36_more_than_4_debiased'] >= sfr_sample['t11_arms_number_a32_2_debiased']) & \
                       (sfr_sample['t11_arms_number_a36_more_than_4_debiased'] >= sfr_sample['t11_arms_number_a33_3_debiased']) & \
                       (sfr_sample['t11_arms_number_a36_more_than_4_debiased'] >= sfr_sample['t11_arms_number_a34_4_debiased']) & \
                       (sfr_sample['t11_arms_number_a36_more_than_4_debiased'] >= sfr_sample['t11_arms_number_a31_1_debiased']) & \
                       (sfr_sample['t11_arms_number_a36_more_than_4_debiased'] >= sfr_sample['t11_arms_number_a37_cant_tell_debiased']) ]

    an_x = sfr_sample[spiral & \
                       (sfr_sample['t11_arms_number_a37_cant_tell_debiased'] >= sfr_sample['t11_arms_number_a32_2_debiased']) & \
                       (sfr_sample['t11_arms_number_a37_cant_tell_debiased'] >= sfr_sample['t11_arms_number_a33_3_debiased']) & \
                       (sfr_sample['t11_arms_number_a37_cant_tell_debiased'] >= sfr_sample['t11_arms_number_a34_4_debiased']) & \
                       (sfr_sample['t11_arms_number_a37_cant_tell_debiased'] >= sfr_sample['t11_arms_number_a36_more_than_4_debiased']) & \
                       (sfr_sample['t11_arms_number_a37_cant_tell_debiased'] >= sfr_sample['t11_arms_number_a31_1_debiased']) ]

    aw_t = sfr_sample[spiral & \
                       (sfr_sample['t10_arms_winding_a28_tight_debiased'] >= sfr_sample['t10_arms_winding_a29_medium_debiased']) & \
                       (sfr_sample['t10_arms_winding_a28_tight_debiased'] >= sfr_sample['t10_arms_winding_a30_loose_debiased'])]

    aw_m = sfr_sample[spiral & \
                       (sfr_sample['t10_arms_winding_a29_medium_debiased'] >= sfr_sample['t10_arms_winding_a28_tight_debiased']) & \
                       (sfr_sample['t10_arms_winding_a29_medium_debiased'] >= sfr_sample['t10_arms_winding_a30_loose_debiased'])]

    aw_l = sfr_sample[spiral & \
                       (sfr_sample['t10_arms_winding_a30_loose_debiased'] >= sfr_sample['t10_arms_winding_a29_medium_debiased']) & \
                       (sfr_sample['t10_arms_winding_a30_loose_debiased'] >= sfr_sample['t10_arms_winding_a28_tight_debiased'])]

    aw_l = sfr_sample[spiral & \
                       (sfr_sample['t10_arms_winding_a30_loose_debiased'] >= sfr_sample['t10_arms_winding_a29_medium_debiased']) & \
                       (sfr_sample['t10_arms_winding_a30_loose_debiased'] >= sfr_sample['t10_arms_winding_a28_tight_debiased'])]


    notedgeon = (sfr_sample['t01_smooth_or_features_a02_features_or_disk_debiased'] > 0.430) & (sfr_sample['t02_edgeon_a05_no_debiased'] > 0.715) & (sfr_sample['t02_edgeon_a05_no_weight'] >= 20)

    barred = sfr_sample[notedgeon & (sfr_sample['t03_bar_a06_bar_debiased'] >= 0.5)] 
    unbarred = sfr_sample[notedgeon & (sfr_sample['t03_bar_a06_bar_debiased'] < 0.5)] 

    with fits.open('%s/mergers/mergers_fracdev.fits' % gzm_path) as f:
        data = f[1].data

    sf_mergers = data[(data['bpt'] == 1)]

    axc = fig.add_subplot(111)    # The big subplot
    axc.spines['top'].set_color('none')
    axc.spines['bottom'].set_color('none')
    axc.spines['left'].set_color('none')
    axc.spines['right'].set_color('none')
    axc.tick_params(labelcolor='none', top='off', bottom='off', left='off', right='off')
    axc.set_xlabel(r'$f_{DeV}$ (r-band)',labelpad=10,fontsize=20)
    axc.set_ylabel('Normalized cumulative sum',labelpad=10,fontsize=20)

    axc.set_title('frac deV CDF for GZ2 galaxies',fontsize=25)

    nbins = 20

    ax = fig.add_subplot(221)
    n, bins, patches = ax.hist(sfr_sample['FRACDEV_R'], nbins, histtype='step', cumulative=True, normed=True, edgecolor='black', alpha=1.0, lw=3)
    ax.get_xaxis().set_ticks([])
    ax.get_yaxis().set_ticks(np.arange(6)*0.2)
    n_sub, bins_sub, patches_sub = ax.hist(an_1['FRACDEV_R'], nbins, histtype='step', cumulative=True, normed=True, edgecolor=an_colors[0], alpha=1.0, lw=1)
    n_sub, bins_sub, patches_sub = ax.hist(an_2['FRACDEV_R'], nbins, histtype='step', cumulative=True, normed=True, edgecolor=an_colors[1], alpha=1.0, lw=1)
    n_sub, bins_sub, patches_sub = ax.hist(an_3['FRACDEV_R'], nbins, histtype='step', cumulative=True, normed=True, edgecolor=an_colors[2], alpha=1.0, lw=1)
    n_sub, bins_sub, patches_sub = ax.hist(an_4['FRACDEV_R'], nbins, histtype='step', cumulative=True, normed=True, edgecolor=an_colors[3], alpha=1.0, lw=1)
    n_sub, bins_sub, patches_sub = ax.hist(an_5['FRACDEV_R'], nbins, histtype='step', cumulative=True, normed=True, edgecolor=an_colors[4], alpha=1.0, lw=1)
    n_sub, bins_sub, patches_sub = ax.hist(an_x['FRACDEV_R'], nbins, histtype='step', cumulative=True, normed=True, edgecolor=an_colors[5], alpha=1.0, lw=1)
    ax.text(0.50,0.40,'Arms number',fontsize=16,ha='left')

    ax = fig.add_subplot(222)
    n, bins, patches = ax.hist(sfr_sample['FRACDEV_R'], nbins, histtype='step', cumulative=True, normed=True, edgecolor='black', alpha=1.0, lw=3)
    ax.get_xaxis().set_ticks([])
    ax.get_yaxis().set_ticks([])
    n_sub, bins_sub, patches_sub = ax.hist(aw_t['FRACDEV_R'], nbins, histtype='step', cumulative=True, normed=True, edgecolor=aw_colors[0], alpha=1.0, lw=1)
    n_sub, bins_sub, patches_sub = ax.hist(aw_m['FRACDEV_R'], nbins, histtype='step', cumulative=True, normed=True, edgecolor=aw_colors[1], alpha=1.0, lw=1)
    n_sub, bins_sub, patches_sub = ax.hist(aw_l['FRACDEV_R'], nbins, histtype='step', cumulative=True, normed=True, edgecolor=aw_colors[2], alpha=1.0, lw=1)
    ax.text(0.50,0.40,'Arms winding',fontsize=16,ha='left')

    ax = fig.add_subplot(223)
    ax.get_xaxis().set_ticks(np.arange(5)*0.2)
    ax.get_yaxis().set_ticks(np.arange(5)*0.2)
    n, bins, patches = ax.hist(sfr_sample['FRACDEV_R'], nbins, histtype='step', cumulative=True, normed=True, edgecolor='black', alpha=1.0, lw=3)
    n_sub, bins_sub, patches_sub = ax.hist(barred['FRACDEV_R'], nbins, histtype='step', cumulative=True, normed=True, edgecolor='blue', alpha=1.0, lw=1)
    n_sub, bins_sub, patches_sub = ax.hist(unbarred['FRACDEV_R'], nbins, histtype='step', cumulative=True, normed=True, edgecolor='red', alpha=1.0, lw=1)
    ax.text(0.50,0.40,'Bars',fontsize=16,ha='left')

    ax = fig.add_subplot(224)
    ax.get_xaxis().set_ticks(np.arange(6)*0.2)
    ax.get_yaxis().set_ticks([])
    n, bins, patches = ax.hist(sfr_sample['FRACDEV_R'], nbins, histtype='step', cumulative=True, normed=True, edgecolor='black', alpha=1.0, lw=3)
    n_sub, bins_sub, patches_sub = ax.hist(sf_mergers['FRACDEV_R'], nbins, histtype='step', cumulative=True, normed=True, edgecolor='red', alpha=1.0, lw=1)
    ax.text(0.50,0.40,'Mergers',fontsize=16,ha='left')

    plt.show()

    fig.savefig('%s/fracdev_cdf.pdf' % fig_path, dpi=200)

    return None

def tm_bar_trigger(sfr_sample,weighted=False,contour=False):

    '''
    Idea from Tom Melvin:

    I would be interested to see what the relationships for 1 armed spirals and merging galaxies would look like for barred and unbarred versions of the two. As there is the idea that mergers can induce bars, do merging disk galaxies with bars deviate further from the SFMS or not? I'm not sure of the numbers for each of the samples once plit into barred and unbarred, but it will probably be dependent of mass ratios (as you use in Fig 4), as 1-to-1 mergers would probably have no bars!
    '''

    # Plot

    fig = plt.figure(11,(12,10))
    fig.clf()

    fig.subplots_adjust(left=0.08,bottom=0.15,right=0.9,hspace=0,wspace=0)

    mass,sfr,sfr_err = get_mass_sfr(sfr_sample)
    mass_bins,sfr_bins = bins()
    h,xedges,yedges = np.histogram2d(mass,sfr,bins=(mass_bins,sfr_bins))

    # Plot each one

    responses = ('a31_1','a32_2','a33_3','a34_4','a36_more_than_4','a37_cant_tell')
    arm_tasks = tuple(['t11_arms_number_'+r for r in responses])
    arm_label = ('1','2','3','4','5+','??')
    colors = ('red','orange','yellow','green','blue','purple')

    # Find 1-armed galaxies, then split into barred and unbarred

    spiral = (sfr_sample['t01_smooth_or_features_a02_features_or_disk_debiased'] > 0.430) & (sfr_sample['t02_edgeon_a05_no_debiased'] > 0.715) & (sfr_sample['t04_spiral_a08_spiral_weight'] >= 20) & (sfr_sample['t04_spiral_a08_spiral_debiased'] > 0.619)
    an_1 = (sfr_sample['t11_arms_number_a31_1_debiased'] >= sfr_sample['t11_arms_number_a32_2_debiased']) & \
                (sfr_sample['t11_arms_number_a31_1_debiased'] >= sfr_sample['t11_arms_number_a33_3_debiased']) & \
                (sfr_sample['t11_arms_number_a31_1_debiased'] >= sfr_sample['t11_arms_number_a34_4_debiased']) & \
                (sfr_sample['t11_arms_number_a31_1_debiased'] >= sfr_sample['t11_arms_number_a36_more_than_4_debiased']) & \
                (sfr_sample['t11_arms_number_a31_1_debiased'] >= sfr_sample['t11_arms_number_a37_cant_tell_debiased'])
    barred = (sfr_sample['t03_bar_a06_bar_debiased'] >= 0.4)
    unbarred = (sfr_sample['t03_bar_a06_bar_debiased'] < 0.4)

    axc = fig.add_subplot(111)    # The big subplot
    axc.spines['top'].set_color('none')
    axc.spines['bottom'].set_color('none')
    axc.spines['left'].set_color('none')
    axc.spines['right'].set_color('none')
    axc.tick_params(labelcolor='none', top='off', bottom='off', left='off', right='off')
    axc.set_xlabel('Stellar mass [log '+r'$\/M/M_\odot$]',labelpad=10,fontsize=20)
    axc.set_ylabel('SFR '+r'$[\log\/M_\odot/\mathrm{yr}]$',labelpad=3,fontsize=20)

    # 1-armed spirals: barred and unbarred

    ax1 = fig.add_subplot(221)
    h = ax1.hist2d(mass,sfr,bins=50,cmap = cm.gray_r, norm=LogNorm())
    ax1.set_xlim(6,11.5)
    ax1.set_ylim(-3.9,2)
    ax1.get_xaxis().set_ticks([])
    onearm_nobar = sfr_sample[spiral & an_1 & unbarred]
    ax1.scatter(onearm_nobar['MEDIAN_MASS'],onearm_nobar['MEDIAN_SFR'], s = 2, color='red', marker='o')
    plot_fits('SF galaxies',sfr_sample,ax1,'black',lw=1,ls='-')
    plot_fits('1-armed unbarred',onearm_nobar,ax1,'red')
    ax1.text(6.2,1.5,'1-armed, unbarred (%i)' % len(onearm_nobar),ha='left',fontsize=16)

    ax2 = fig.add_subplot(222)
    h = ax2.hist2d(mass,sfr,bins=50,cmap = cm.gray_r, norm=LogNorm())
    ax2.set_xlim(6,11.5)
    ax2.set_ylim(-3.9,2)
    ax2.get_xaxis().set_ticks([])
    ax2.get_yaxis().set_ticks([])
    onearm_bar = sfr_sample[spiral & an_1 & barred]
    ax2.scatter(onearm_bar['MEDIAN_MASS'],onearm_bar['MEDIAN_SFR'], s = 2, color='blue', marker='o')
    plot_fits('SF galaxies',sfr_sample,ax2,'black',lw=1,ls='-')
    plot_fits('1-armed unbarred',onearm_bar,ax2,'blue')
    ax2.text(6.2,1.5,'1-armed, barred (%i)' % len(onearm_bar),ha='left',fontsize=16)

    # Merging galaxies: barred and unbarred

    with fits.open('%s/mergers/mergers_gz2.fits' % gzm_path) as f:
        data = f[1].data

    sf_mergers = (data['bpt'] == 1)
    barred_m = (data['t03_bar_a06_bar_debiased'] >= 0.4)
    unbarred_m = (data['t03_bar_a06_bar_debiased'] < 0.4)

    ax3 = fig.add_subplot(223)
    h = ax3.hist2d(mass,sfr,bins=50,cmap = cm.gray_r, norm=LogNorm())
    ax3.set_xlim(6,11.5)
    ax3.set_ylim(-3.9,2)
    merger_nobar = data[sf_mergers & unbarred_m]
    mb = ax3.scatter(merger_nobar['MEDIAN_MASS'],merger_nobar['MEDIAN_SFR'],c=merger_nobar['mass_ratio'], edgecolor='none',s = 50, marker='.', cmap=matplotlib.cm.RdBu, vmin=1.,vmax=10.)
    plot_fits('SF galaxies',sfr_sample,ax3,'black',lw=1,ls='-')
    plot_fits('Merging unbarred',merger_nobar,ax3,'red',ls='-.')
    ax3.text(6.2,1.5,'Merging, unbarred (%i)' % len(merger_nobar),ha='left',fontsize=16)

    axcb1 = plt.axes([0.40, 0.18, 0.03, 0.12]) 
    cb1 = plt.colorbar(mb,cax = axcb1, orientation="vertical",ticks=[1,3,5,10])
    cb1.set_label('Mass ratio',fontsize=14)

    ax4 = fig.add_subplot(224)
    h = ax4.hist2d(mass,sfr,bins=50,cmap = cm.gray_r, norm=LogNorm())
    ax4.set_xlim(6,11.5)
    ax4.set_ylim(-3.9,2)
    ax4.get_yaxis().set_ticks([])
    merger_bar = data[sf_mergers & barred_m]
    ax4.scatter(merger_bar['MEDIAN_MASS'],merger_bar['MEDIAN_SFR'],c=merger_bar['mass_ratio'], edgecolor='none',s = 50, marker='.', cmap=matplotlib.cm.RdBu, vmin=1.,vmax=10.)
    plot_fits('SF galaxies',sfr_sample,ax4,'black',lw=1,ls='-')
    plot_fits('Merging unbarred',merger_bar,ax4,'blue',ls='-.')
    ax4.text(6.2,1.5,'Merging, barred (%i)' % len(merger_bar),ha='left',fontsize=16)

    axcb2 = plt.axes([0.80, 0.18, 0.03, 0.12]) 
    cb2 = plt.colorbar(mb,cax = axcb2, orientation="vertical",ticks=[1,3,5,10])
    cb2.set_label('Mass ratio',fontsize=14)

    box = axc.get_position()
    axColorbar = plt.axes([box.x1*1.02, box.y0, 0.01, box.height])
    cb = plt.colorbar(h[3],cax = axColorbar, orientation="vertical")
    cb.set_label(r'$N_\mathrm{star-forming\/galaxies}$' ,fontsize=16)

    fig.savefig('%s/tm_bar_trigger.pdf' % fig_path, dpi=200)

    return None

def plot_ms_bulge(sfr_sample,weighted=False,contour=False,plurality=False):

    # Plot

    fig = plt.figure(12,(12,10))
    fig.clf()
    filestr=''

    fig.subplots_adjust(left=0.08,bottom=0.15,hspace=0,wspace=0)

    mass,sfr,sfr_err = get_mass_sfr(sfr_sample)
    mass_bins,sfr_bins = bins()
    h,xedges,yedges = np.histogram2d(mass,sfr,bins=(mass_bins,sfr_bins))

    axc = fig.add_subplot(111)    # The big subplot
    axc.spines['top'].set_color('none')
    axc.spines['bottom'].set_color('none')
    axc.spines['left'].set_color('none')
    axc.spines['right'].set_color('none')
    axc.tick_params(labelcolor='none', top='off', bottom='off', left='off', right='off')
    axc.set_xlabel('Stellar mass [log '+r'$\/M/M_\odot$]',labelpad=10,fontsize=20)
    axc.set_ylabel('SFR '+r'$[\log\/M_\odot/\mathrm{yr}]$',labelpad=3,fontsize=20)

    # Plot each morphological category

    responses = ('a10_no_bulge','a11_just_noticeable','a12_obvious','a13_dominant')
    bulge_tasks = ['t05_bulge_prominence_'+r for r in responses]
    colors = ('red','orange','yellow','green')

    for idx, (a,c) in enumerate(zip(bulge_tasks,colors)):

        bulge_label = a[25:]

        ax = fig.add_subplot(2,2,idx+1)
        h = ax.hist2d(mass,sfr,bins=50,cmap = cm.gray_r, norm=LogNorm())
        ax.set_xlim(6,11.5)
        ax.set_ylim(-4,2)
        if idx in (0,1):
            ax.get_xaxis().set_ticks([])
        if idx in (1,3):
            ax.get_yaxis().set_ticks([])

        rcopy = list(bulge_tasks)
        thistask = rcopy.pop(idx)
        notedgeon = (sfr_sample['t01_smooth_or_features_a02_features_or_disk_debiased'] > 0.430) & (sfr_sample['t02_edgeon_a05_no_debiased'] > 0.715)
        n1 = sfr_sample[notedgeon & (sfr_sample['%s_flag' % a] == 1)] 
        pl = sfr_sample[notedgeon & (sfr_sample['%s_debiased' % a] >= sfr_sample['%s_debiased' % rcopy[0]]) & (sfr_sample['%s_debiased' % a] >= sfr_sample['%s_debiased' % rcopy[1]]) & (sfr_sample['%s_debiased' % a] >= sfr_sample['%s_debiased' % rcopy[2]])] 

        # Two sets of plots: one weights histogram by debiased vote fraction per galaxy; other shows discrete categories from GZ2 flags.
        if weighted:
            filestr='_weighted'
            disks = sfr_sample[notedgeon]
            if contour:
                hc,xc,yc = np.histogram2d(disks['MEDIAN_MASS'],disks['MEDIAN_SFR'],bins=(mass_bins,sfr_bins),weights=disks['%s_debiased' % a])
                levels=10**(np.linspace(0,3,12))
                CS = ax.contour(mass_bins[1:],sfr_bins[1:],hc.T,levels,colors=c)
                filestr += '_contour'
            else:
                h = ax.hist2d(disks['MEDIAN_MASS'],disks['MEDIAN_SFR'],bins=50,cmap = cm.RdYlGn, weights=disks['%s_debiased' % a],vmin=0.01,vmax=100.,norm=LogNorm())
            plot_fits(bulge_label,disks,ax,c,morph=a,weight_by_err=False,weight_by_morph=True)
        else:
            filestr = ''
            if plurality:
                plotset = pl
                filestr += '_plurality'
            else:
                plotset = n1

            ax.scatter(plotset['MEDIAN_MASS'],plotset['MEDIAN_SFR'], s = 2, color=c, marker='o')
            try:
                plot_fits(bulge_label,plotset,ax,c,morph=a)
            except LinAlgError:
                print 'Insufficient number of points (%i) to fit %s data' % (len(n1),bulge_label)

        ax.text(6.2,1.3,bulge_label, color='k')

        # Plot the best linear fits

        plot_fits(bulge_label,sfr_sample,ax,'black',lw=1,ls='-')

    # Set the colorbar and labels at the end

    box = axc.get_position()
    axColorbar = plt.axes([box.x1*1.02, box.y0, 0.01, box.height])
    cb = plt.colorbar(h[3],cax = axColorbar, orientation="vertical")
    cb.set_label(r'$N_\mathrm{star-forming\/galaxies}$' ,fontsize=16)

    fig.savefig('%s/ms_bulge%s.pdf' % (fig_path,filestr), dpi=200)

    return None

def inclination_reddening():

    # What is the distribution of inclination angles for the various morphologies?

    # Get data from CasJobs-matched file
    filename = '%s/mpajhu_gz2_axisratios.fits' % fits_path
    with fits.open(filename) as f:
        data = f[1].data

    # Star-forming galaxies only
    sf = (data['bpt'] == 1) #| (data['bpt'] == 2)
    redshift = data['REDSHIFT'] <= 0.1
    absmag = data['PETROMAG_MR'] < -19.5

    sfr_sample = data[sf & redshift]

    # Set up plots

    fig = plt.figure(13,(12,6))
    fig.clf()

    fig.subplots_adjust(left=0.08,bottom=0.15,hspace=0,wspace=0)

    axc = fig.add_subplot(111)    # The big subplot
    axc.spines['top'].set_color('none')
    axc.spines['bottom'].set_color('none')
    axc.spines['left'].set_color('none')
    axc.spines['right'].set_color('none')
    axc.tick_params(labelcolor='none', top='off', bottom='off', left='off', right='off')
    axc.set_xlabel('Inclination angle [deg] (deproj. r-band axis ratio, exp. fit)',labelpad=10,fontsize=20)
    axc.set_ylabel('Count',labelpad=10,fontsize=20)

    # Disks and bars
    notedgeon = (sfr_sample['t01_smooth_or_features_a02_features_or_disk_debiased'] > 0.430) & (sfr_sample['t02_edgeon_a05_no_debiased'] > 0.715) & (sfr_sample['t02_edgeon_a05_no_weight'] >= 20)
    barred = sfr_sample[notedgeon & (sfr_sample['t03_bar_a06_bar_debiased'] >= 0.4)] 
    unbarred = sfr_sample[notedgeon & (sfr_sample['t03_bar_a06_bar_debiased'] < 0.4)] 

    # Spiral arms
    spiral = (sfr_sample['t01_smooth_or_features_a02_features_or_disk_debiased'] > 0.430) & (sfr_sample['t02_edgeon_a05_no_debiased'] > 0.715) & (sfr_sample['t04_spiral_a08_spiral_weight'] >= 20) & (sfr_sample['t04_spiral_a08_spiral_debiased'] > 0.619)
    #n1 = sfr_sample[spiral & (sfr_sample['%s_flag' % a] == 1)] 

    # Find mean,std for each sample

    print '\nexp A/B: \n'

    print 'All star-forming galaxies (N = %6i): mean = %.2f +- %.2f' % (len(sfr_sample),np.mean(sfr_sample['expAB_r']),np.std(sfr_sample['expAB_r']))
    print 'All         disk galaxies (N = %6i): mean = %.2f +- %.2f' % (notedgeon.sum(),np.mean(sfr_sample[notedgeon]['expAB_r']),np.std(sfr_sample[notedgeon]['expAB_r']))
    print 'All       spiral galaxies (N = %6i): mean = %.2f +- %.2f' % (spiral.sum(),np.mean(sfr_sample[spiral]['expAB_r']),np.std(sfr_sample[spiral]['expAB_r']))

    print ''
    print 'Arms number: '

    nbins=15
    rad2deg = 180./np.pi

    ax1 = fig.add_subplot(131)
    ax1.get_xaxis().set_ticks(np.arange(10)*10.)
    ax1.set_title('Arms number')

    for idx,(an,anc) in enumerate(zip(an_tasks,an_colors)):

        rcopy = list(an_tasks)
        thistask = rcopy.pop(idx)
        pl = sfr_sample[spiral & (sfr_sample['%s_debiased' % an] >= sfr_sample['%s_debiased' % rcopy[0]]) & (sfr_sample['%s_debiased' % an] >= sfr_sample['%s_debiased' % rcopy[1]]) & (sfr_sample['%s_debiased' % an] >= sfr_sample['%s_debiased' % rcopy[2]]) & (sfr_sample['%s_debiased' % an] >= sfr_sample['%s_debiased' % rcopy[3]]) & (sfr_sample['%s_debiased' % an] >= sfr_sample['%s_debiased' % rcopy[4]])] 

        # Check with KS test - does it deviate from the broader sample of spirals?
        d,p = ks_2samp(sfr_sample[spiral]['expAB_R'],pl['expAB_r'])

        print '\t%12s arms (N = %6i): mean = %.2f +- %.2f; KS-prob from all spirals = %.6f' % (an[20:],len(pl),np.mean(pl['expAB_r']),np.std(pl['expAB_r']),p)

        histML(np.arccos(pl['expAB_r'])*rad2deg, bins=nbins, ax=ax1, histtype='stepfilled', color=anc,range=(0,90),alpha=0.4)

    histML(np.arccos(sfr_sample[spiral]['expAB_r'])*rad2deg, bins=nbins, ax=ax1, histtype='step', color='k',range=(0,90),lw=3)

    print ''
    print 'Arms winding: '

    ax2 = fig.add_subplot(132)
    ax2.get_xaxis().set_ticks(np.arange(10)*10.)
    ax2.get_yaxis().set_ticks([])
    ax2.set_title('Arms winding')

    for idx,(aw,awc) in enumerate(zip(aw_tasks,aw_colors)):

        rcopy = list(aw_tasks)
        thistask = rcopy.pop(idx)
        pl = sfr_sample[spiral & (sfr_sample['%s_debiased' % aw] >= sfr_sample['%s_debiased' % rcopy[0]]) & (sfr_sample['%s_debiased' % aw] >= sfr_sample['%s_debiased' % rcopy[1]])] 

        # Check with KS test - does it deviate from the broader sample of spirals?
        d,p = ks_2samp(sfr_sample[spiral]['expAB_R'],pl['expAB_r'])

        print '\t%12s arms (N = %6i): mean = %.2f +- %.2f; KS-prob from all spirals = %.6f' % (aw[21:],len(pl),np.mean(pl['expAB_r']),np.std(pl['expAB_r']),p)

        histML(np.arccos(pl['expAB_r'])*rad2deg, bins=nbins, ax=ax2, histtype='stepfilled', color=awc, range=(0,90),alpha=0.4)

    histML(np.arccos(sfr_sample[spiral]['expAB_r'])*rad2deg, bins=nbins, ax=ax2, histtype='step', color='k',range=(0,90),lw=3)

    print ''
    print 'Bars: '

    ax3 = fig.add_subplot(133)
    ax3.get_yaxis().set_ticks([])
    ax3.set_title('Bars')

    # Check with KS test - does it deviate from the broader sample of disks?
    db,pb = ks_2samp(sfr_sample[notedgeon]['expAB_R'],barred['expAB_r'])
    du,pu = ks_2samp(sfr_sample[notedgeon]['expAB_R'],unbarred['expAB_r'])

    histML(np.arccos(barred['expAB_r'])*rad2deg, bins=nbins, ax=ax3, histtype='stepfilled', color='blue', range=(0,90),alpha=0.4)
    histML(np.arccos(unbarred['expAB_r'])*rad2deg, bins=nbins, ax=ax3, histtype='stepfilled', color='red', range=(0,90),alpha=0.4)
    histML(np.arccos(sfr_sample[notedgeon]['expAB_r'])*rad2deg, bins=nbins, ax=ax3, histtype='step', color='k',range=(0,90),lw=3)

    print 'Barred   (N = %6i): mean = %.2f +- %.2f; KS-prob from all not edge-on feature/disks = %.6f' % (len(barred),np.mean(barred['expAB_r']),np.std(barred['expAB_r']),pb)
    print 'Unbarred (N = %6i): mean = %.2f +- %.2f; KS-prob from all not edge-on feature/disks = %.6f' % (len(unbarred),np.mean(unbarred['expAB_r']),np.std(unbarred['expAB_r']),pu)

    for ax in (ax1,ax2,ax3):
        ax.set_ylim(0,2000)


    fig.savefig('%s/inclination_reddening.pdf' % fig_path, dpi=200)

    return None
