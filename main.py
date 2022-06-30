#!/usr/bin/env python
# -*- coding: latin-1 -*-

"""Something must be here?"""
import atexit
import os
from os.path import join
import codecs
import csv
import random

from statistics import mean

import yaml
from psychopy import visual, event, logging, gui, core

from misc.screen_misc import get_screen_res, get_frame_rate
from itertools import combinations_with_replacement, product


@atexit.register
def save_beh_results():
    """
    Save results of experiment. Decorated with @atexit in order to make sure, that intermediate
    results will be saved even if interpreter will broke.
    """
    with open(join('results', PART_ID + '_' + str(random.choice(range(100, 1000))) + '_beh.csv'), 'w',
              encoding='utf-8') as beh_file:
        beh_writer = csv.writer(beh_file)
        beh_writer.writerows(RESULTS)
    logging.flush()


def show_image(win, file_name, size, key='e'):
    """
    Show an image or instructions in a form of an image.
    """
    image = visual.ImageStim(win=win, image=file_name,
                             interpolate=True, units="pix", size=size)
    image.draw()
    win.flip()
    clicked = event.waitKeys(keyList=[key, 'space'])
    if clicked == [key]:
        logging.critical(
            'Experiment finished by user! {} pressed.'.format(key[0]))
        exit(0)
    win.flip()


def read_text_from_file(file_name, insert=''):
    """
    Method that read message from text file, and optionally add some
    dynamically generated info.
    :param file_name: Name of file to read
    :param insert:
    :return: message
    """
    if not isinstance(file_name, str):
        logging.error('Problem with file reading, filename must be a string')
        raise TypeError('file_name must be a string')
    msg = list()
    with codecs.open(file_name, encoding='utf-8', mode='r') as data_file:
        for line in data_file:
            if not line.startswith('#'):  # if not commented line
                if line.startswith('<--insert-->'):
                    if insert:
                        msg.append(insert)
                else:
                    msg.append(line)
    return ''.join(msg)


def check_exit(key='e'):
    """
    Check (during procedure) if experimentator doesn't want to terminate.
    """
    stop = event.getKeys(keyList=[key])
    if stop:
        abort_with_error(
            'Experiment finished by user! {} pressed.'.format(key))


def show_info(win, file_name, insert=''):
    """
    Clear way to show info message into screen.
    :param win:
    :return:
    """
    msg = read_text_from_file(file_name, insert=insert)
    msg = visual.TextStim(win, color='black', text=msg,
                          height=0.020, wrapWidth=SCREEN_RES['width'])
    msg.draw()
    win.flip()
    key = event.waitKeys(keyList=['space'])
    if key == ['e']:
        abort_with_error(
            'Experiment finished by user on info screen! e pressed.')
    win.flip()


def abort_with_error(err):
    """
    Call if an error occured.
    """
    logging.critical(err)
    raise Exception(err)


# GLOBALS

RESULTS = list()  # list in which data will be colected
RESULTS.append(['PART_ID', 'Trial_no', "Key pressed", 'Reaction time', "Correct", "Congruency", "Session"])


def main():
    global PART_ID  # PART_ID is used in case of error on @atexit, that's why it must be global

    # === Dialog popup ===
    info = {'IDENTYFIKATOR': '', u'P\u0141EC': ['M', "K"], 'WIEK': ''}
    dictDlg = gui.DlgFromDict(
        dictionary=info, title='Experiment title, fill by your name!')
    if not dictDlg.OK:
        abort_with_error('Info dialog terminated.')

    clock = core.Clock()
    # load config, all params are there
    conf = yaml.load(open('config.yaml', encoding='utf-8'), Loader=yaml.FullLoader)

    # === Scene init ===
    win = visual.Window(list(SCREEN_RES.values()), fullscr=True, monitor='testMonitor', units='height',
                        screen=0, color=conf['BACKGROUND_COLOR'])
    event.Mouse(visible=False, newPos=None, win=win)  # Make mouse invisible
    FRAME_RATE = get_frame_rate(win)

    # check if a detected frame rate is consistent with a frame rate for witch experiment was designed
    # important only if milisecond precision design is used
    if FRAME_RATE != conf['FRAME_RATE']:
        dlg = gui.Dlg(title="Critical error")
        dlg.addText(
            'Wrong no of frames detected: {}. Experiment terminated.'.format(FRAME_RATE))
        dlg.show()
        return None

    PART_ID = info['IDENTYFIKATOR'] + info[u'P\u0141EC'] + info['WIEK']
    logging.LogFile(join('results', PART_ID + '.log'),
                    level=logging.INFO)  # errors logging
    logging.info('FRAME RATE: {}'.format(FRAME_RATE))
    logging.info('SCREEN RES: {}'.format(SCREEN_RES.values()))

    stim = visual.TextStim(win, text="", height=conf["STIM_SIZE"], color=conf["STIM_COLOR"])
    fix_cross = visual.TextStim(win, text="+", height=conf["FIX_CROSS_SIZE"], color=conf["FIX_CROSS_COLOR"])

    show_info(win, join('.', 'messages', 'hello.txt'))
    trial_no = 0
    trial_no += 1

    show_info(win, join('.', 'messages', 'before_training.txt'))

    for _ in range(conf['NO_TRAINING_TRIALS']):
        stim.text = random.choice(conf['STIM_LETTERS'])
        key_pressed, rt, corr, congr = run_trial(win, conf, stim, clock, fix_cross)
        RESULTS.append([PART_ID, trial_no, key_pressed, rt, corr, congr, "training"])

        # it's often good presenting feedback in trening trials
        if key_pressed in conf["REACTION_KEYS"]:
            feedb = "Poprawnie" if corr else "Niepoprawnie"
        else:
            feedb = "Za wolno!"

        feedb = visual.TextStim(win, text=feedb, height=0.025,
                                color=conf['FIX_CROSS_COLOR'])
        feedb.draw()
        win.flip()
        core.wait(1)
        win.flip()

        trial_no += 1

        # === Experiment ===

    for _ in range(conf["INTERSTIM_TIME"]):
        win.flip()

    show_info(win, join('.', 'messages', 'before_experiment.txt'))

    # stimuli:
    left_congr = [conf["STIM_LETTERS"][0]]
    right_congr = [conf["STIM_LETTERS"][1]]
    left_incongr = [conf["STIM_LETTERS"][3]]
    right_incongr = [conf["STIM_LETTERS"][2]]

    # stimuli proportions:
    left_congr_prop = conf["LEFT_CONG_PROPORTION"]
    right_congr_prop = conf["RIGHT_CONG_PROPORTION"]
    left_incongr_prop = conf["LEFT_INCONG_PROPORTION"]
    right_incongr_prop = conf["RIGHT_INCONG_PROPORTION"]
    
    #stimuli list with proportions set:
    stim_seq_experiment = left_congr * left_congr_prop + right_congr * right_congr_prop + left_incongr * left_incongr_prop + right_incongr * right_incongr_prop

    for block_no in range(conf['NO_BLOCKS']):
        random.shuffle(stim_seq_experiment)
        for i in stim_seq_experiment:
            stim.text = i
            key_pressed, rt, corr, congr = run_trial(win, conf, stim, clock, fix_cross)
            RESULTS.append([PART_ID, trial_no, key_pressed, rt, corr, congr, "experiment"])
            trial_no += 1
        if block_no < conf["NO_BLOCKS"] - 1:
            show_image(win, os.path.join('.', 'images', 'break.jpg'),
                       size=(SCREEN_RES['width'], SCREEN_RES['height']))

        # === Cleaning time ===
    save_beh_results()
    logging.flush()

    for _ in range(conf["INTERSTIM_TIME"]):
        win.flip()

    show_info(win, join('.', 'messages', 'end.txt'))
    win.close()


def run_trial(win, conf, stim, clock, fix_cross):

    for _ in range(conf["FIX_CROSS_TIME"]):
        fix_cross.draw()
        win.flip()

    event.clearEvents()

    win.callOnFlip(clock.reset)

    for _ in range(conf['STIM_TIME']):  # present stimuli
        check_exit()
        reaction = event.getKeys(keyList=list(
            conf['REACTION_KEYS']), timeStamped=clock)
        if reaction:  # break if any button was pressed
            break
        stim.draw()
        win.flip()

    # === Trial ended, prepare data for send  ===
    if reaction:
        key_pressed, rt = reaction[0]
    else:  # timeout
        key_pressed = 'no_key'
        rt = -1.0

    # reactions:
    reaction_left = conf["REACTION_KEYS"][0]
    reaction_right = conf["REACTION_KEYS"][1]

    # stimuli:
    left_congr = conf["STIM_LETTERS"][0]
    right_congr = conf["STIM_LETTERS"][1]
    left_incongr = conf["STIM_LETTERS"][3]
    right_incongr = conf["STIM_LETTERS"][2]

    # trial correct if:
    cond1 = key_pressed == reaction_left and (
            stim.text == left_congr or stim.text == left_incongr)
    # or
    cond2 = key_pressed == reaction_right and (
            stim.text == right_congr or stim.text == right_incongr)

    if cond1 or cond2:
        corr = True
    else:
        corr = False

    if stim.text in [conf["STIM_LETTERS"][0], conf["STIM_LETTERS"][1]]:
        congr = True
    else:
        congr = False

    return key_pressed, rt, corr, congr  # return all data collected during trial


if __name__ == '__main__':
    PART_ID = ''
    SCREEN_RES = get_screen_res()
    main()
