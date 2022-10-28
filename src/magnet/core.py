import numpy as np
import torch
from magnet.net import model, model_lstm, model_transformer
from magnet import config as c


def default_units(prop):  # Probably we are not going to need the default units
    prop = prop.lower().strip()
    return {
        'frequency': 'Hz',
        'flux_density': 'T',
        'power_loss': '[W/m^3]'
    }[prop]


def plot_label(prop):
    prop = prop.lower().strip()
    return {
        'frequency_khz': 'Frequency [kHz]',
        'flux_density_mt': 'AC Flux Density [mT]',
        'power_loss_kw/m3': 'Power Loss [kW/m^3]',
        'frequency': 'Frequency [Hz]',
        'flux_density': 'AC Flux Density [T]',
        'power_loss': 'Power Loss [W/m^3]',
        'duty_ratio': 'Duty Ratio'
    }[prop]


def plot_title(prop):
    prop = prop.lower().strip()
    return {
        'frequency_khz': 'Frequency',
        'flux_density_mt': 'Flux Density',
        'power_loss_kw/m3': 'Power Loss',
        'frequency': 'Frequency',
        'flux_density': 'Flux Density',
        'power_loss': 'Power Loss'
    }[prop]


def core_loss_default(material, freq, flux, temp, bias, duty=None):
    bdata = bdata_generation(flux, duty)
    hdata = BH_Transformer(material, freq, temp, bias, bdata)
    core_loss = loss_BH(bdata, hdata, freq)
    return core_loss


def core_loss_arbitrary(material, freq, flux, temp, bias, duty):
    bdata_pre = np.interp(np.linspace(0, 1, c.streamlit.n_nn), np.array(duty), np.array(flux))
    bdata = bdata_pre - np.average(bdata_pre)
    hdata = BH_Transformer(material, freq, temp, bias, bdata)
    core_loss = loss_BH(bdata, hdata, freq)
    return core_loss


def BH_Transformer(material, freq, temp, bias, bdata):
    net_encoder, net_decoder, norm = model_transformer(material)
        
    bdata = torch.from_numpy(np.array(bdata)).float()
    bdata = (bdata-norm[0])/norm[1]
    bdata = bdata.unsqueeze(0).unsqueeze(2)
    
    freq = np.log10(freq)
    freq = torch.from_numpy(np.array(freq)).float()
    freq = (freq-norm[2])/norm[3]
    freq = freq.unsqueeze(0).unsqueeze(1)
    
    temp = torch.from_numpy(np.array(temp)).float()
    temp = (temp-norm[4])/norm[5]
    temp = temp.unsqueeze(0).unsqueeze(1)
    
    bias = torch.from_numpy(np.array(bias)).float()
    bias = (bias-norm[6])/norm[7]
    bias = bias.unsqueeze(0).unsqueeze(1)
        
    outputs = torch.zeros(1, bdata.size()[1]+1, 1)
    tgt = (torch.rand(1, bdata.size()[1]+1, 1)*2-1)
    tgt[:, 0, :] = 0.1*torch.ones(tgt[:, 0, :].size())
    
    src = net_encoder(src=bdata, tgt=tgt, var=torch.cat((freq, temp, bias), dim=1))
    
    for t in range(1, bdata.size()[1]+1):   
        outputs = net_decoder(src=src, tgt=tgt, var=torch.cat((freq, temp, bias), dim=1))
        tgt[:, t, :] = outputs[:, t-1, :]
        
    outputs = net_decoder(src, tgt, torch.cat((freq, temp, bias), dim=1))
    
    hdata = (outputs[:, :-1, :]*norm[9]+norm[8]).squeeze(2).squeeze(0).detach().numpy()
    
    return hdata


def loss_BH(bdata, hdata, freq):
    loss = freq * np.trapz(hdata, bdata)
    return loss


def bdata_generation(flux, duty=None, n_points=c.streamlit.n_nn):
    # Here duty is not needed, but it is convenient to call the function recursively

    if duty is None:  # Sinusoidal
        bdata = flux * np.sin(np.linspace(0.0, 2 * np.pi, n_points))
    elif type(duty) is list:  # Trapezoidal
        assert len(duty) == 3, 'Please specify 3 values as the Duty Ratios'
        assert np.all((0 <= np.array(duty)) & (np.array(duty) <= 1)), 'Duty ratios should be between 0 and 1'

        if duty[0] > duty[1]:
            # Since Bpk is proportional to the voltage, and the voltage is proportional to (1-dp+dN) times the dp
            bp = flux
            bn = -bp * ((-1 - duty[0] + duty[1]) * duty[1]) / (
                    (1 - duty[0] + duty[1]) * duty[0])  # proportional to (-1-dp+dN)*dn
        else:
            bn = flux  # proportional to (-1-dP+dN)*dN
            bp = -bn * ((1 - duty[0] + duty[1]) * duty[0]) / (
                    (-1 - duty[0] + duty[1]) * duty[1])  # proportional to (1-dP+dN)*dP
        bdata = np.interp(np.linspace(0, 1, n_points),
                          np.array([0, duty[0], duty[0] + duty[2], 1 - duty[2], 1]),
                          np.array([-bp, bp, bn, -bn, -bp]))
    else:  # type(duty) == 'float' -> Triangular
        assert 0 <= duty <= 1.0, 'Duty ratio should be between 0 and 1'
        bdata = np.interp(np.linspace(0, 1, n_points), np.array([0, duty, 1]), np.array([-flux, flux, -flux]))

    return bdata