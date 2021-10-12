# Coarse Grained questions
cgDict = {}
cgDict['0'] = {}

# Fine Grained passes (dictionary of dictionaries)
fgDict = {}

fgDict['0'] = {'annotationTag': ['Speech'], 'visualization': 'waveform', 'instructions': ["",
'In the fine grained annotation phase, you will be asked to label all parts of the audio where a specific kind of audio is heard. The annotation system will take you through different “passes”, each will ask you to identify different kinds of audio phenomenon. Passes are mostly independent, and you can expect to see the same file in different passes.'
            '<br><br>'
           ' <b><code>Speech Pass</code></b>'
            '<br>'
'Please mark parts of the audio where there is any kind of speech from any source. It is possible (though hopefully rare) for a file to have no speech at all.<br>'
'Speech means “human voice forming words”, regardless of the source of the sound. <br> Speech heard from TV, radio, or phone is still speech. <br>'
          '<ul style="padding-left:2em">'
               '<li><i class="fa fa-arrow-right"></i> These also count as speech: singing, crowds, TV announcers,  a recording.</li>'
               '<li><i class="fa fa-arrow-right"></i> Also speech: unintelligible speech, where you can clearly hear speech but can’t quite understand individual words. Example: people talking in a party.</li>'
               '<li><i class="fa fa-arrow-right"></i> Wordless sounds are not speech: humming a tune, coughing, sneezing, snoring, wordless yelling.</li>'
            '</ul>'

           '<br><hr><hr>'
            '<b>Tool Overview</b>'
           '<ul style="padding-left:2em">'
                '<li><i class="fa fa-arrow-right"></i> Click the play button and listen to the recording.</li>'
                '<li><i class="fa fa-arrow-right"></i> Click and drag on the waveform visualization to create annotations.</li>'
                '<li><i class="fa fa-arrow-right"></i> To drag or resize a region, please first double click on it and make sure that the region is highlighted in green color. You can relisten/delete the region by clicking on the regions’ icons.</li>'
                '<li><i class="fa fa-arrow-right"></i> To delete a label, click on the cross mark located on the label.</li>'
                '<li><i class="fa fa-arrow-right"></i> Once done, click “SUBMIT AND LOAD NEXT RECORDING” to save the annotations and go to the next file.</li>'
                '<li><i class="fa fa-arrow-right"></i> If you are unclear about the file, please click the FLAG button, explain the reason and click submit.</li>'
                '<li><i class="fa fa-arrow-right"></i> Try to be precise when marking the start and end of audio annotations. Try to get within 100 milliseconds of the part (e.g., speech) beginning and ending.</li>'
                '<li><i class="fa fa-arrow-right"></i> You can change the visualization between the waveform (default) and spectrogram.</li>'
                '<li><i class="fa fa-arrow-right"></i> Undo and Redo buttons are available below the visualization</li>'
                            '</ul><br>'
'<b>The progress bar on the bottom of the page shows an overview of the current batch:</b>'
            '<ul style="padding-left:2em">'
               ' <li><i class="fa fa-arrow-right"></i> Check mark (<i class="fa fa-check" style="color:#00C853;"></i>) indicates that the file has been labeled as speech.</li>'
                '<li><i class="fa fa-arrow-right"></i> Cross mark (<i class="fa fa-times" style="color:#007bff;"></i>) indicates that the file has been labeled as notspeech.</li>'
                '<li><i class="fa fa-arrow-right"></i> Explanation mark (<i class="fa fa-exclamation" style="color:#D50000;"></i>) indicates that the file has been flagged.</li>'
                '<li><i class="fa fa-arrow-right"></i> A star mark (<i class="fa fa-star" style="color:grey;"></i>) the end of a batch - a good time to rest or switchtasks.</li>'
                '<li><i class="fa fa-arrow-right"></i> Question mark (<i class="fa fa-question" style="color:#007bff;"></i>) shows the current task.</li>'
                '<li><i class="fa fa-arrow-right"></i> Empty circle means that the task has not been annotated yet.</li>'
            '</ul>'
'<img src="/static/img/progress_bar.png" alt="Progress bar">'
            '<br>'
            '<b>Keyboard shortcuts:</b>'
            '<ul style="padding-left:2em">'
                '<li>&bull;  Play/Pause: Space bar</li>'
                '<li>&bull; Flag: F</li>'
                '<li>&bull; Instructions: I</li>'
            '</ul>'
]}
fgDict['1'] = {'annotationTag': ['TV'], 'visualization': 'waveform', 'instructions': [
    "",
'In the fine grained annotation phase, you will be asked to label all parts of the audio where a specific kind of audio is heard. The annotation system will take you through different “passes”, each will ask you to identify different kinds of audio phenomenon. Passes are mostly independent, and you can expect to see the same file in different passes.'
            '<br><br>'
           ' <b><code>TV Pass</code></b>'
            '<br>'
'Please mark audio coming from TV, phone, computer, radio, and so on, or any recorded audio. You need not limit your selection to just speech -- any audio from TV, for example, can be marked. It is possible for a file to have nothing to mark, in which case you can just move to the next file.<br>'
           '<br> <hr><hr>'
            '<b>Tool Overview</b>'
           '<ul style="padding-left:2em">'
                '<li><i class="fa fa-arrow-right"></i> Click the play button and listen to the recording.</li>'
                '<li><i class="fa fa-arrow-right"></i> Click and drag on the waveform visualization to create annotations.</li>'
                '<li><i class="fa fa-arrow-right"></i> To drag or resize a region, please first double click on it and make sure that the region is highlighted in green color. You can relisten/delete the region by clicking on the regions’ icons.</li>'
                '<li><i class="fa fa-arrow-right"></i> To delete a label, click on the cross mark located on the label.</li>'
                '<li><i class="fa fa-arrow-right"></i> Once done, click “SUBMIT AND LOAD NEXT RECORDING” to save the annotations and go to the next file.</li>'
                '<li><i class="fa fa-arrow-right"></i> If you are unclear about the file, please click the FLAG button, explain the reason and click submit.</li>'
                '<li><i class="fa fa-arrow-right"></i> Try to be precise when marking the start and end of audio annotations. Try to get within 100 milliseconds of the part (e.g., speech) beginning and ending.</li>'
                '<li><i class="fa fa-arrow-right"></i> You can change the visualization between the waveform (default) and spectrogram.</li>'
                '<li><i class="fa fa-arrow-right"></i> Undo and Redo buttons are available below the visualization</li>'
                
            '</ul><br>'
'<b>The progress bar on the bottom of the page shows an overview of the current batch:</b>'
            '<ul style="padding-left:2em">'
               ' <li><i class="fa fa-arrow-right"></i> Check mark (<i class="fa fa-check" style="color:#00C853;"></i>) indicates that the file has been labeled as speech.</li>'
                '<li><i class="fa fa-arrow-right"></i> Cross mark (<i class="fa fa-times" style="color:#007bff;"></i>) indicates that the file has been labeled as notspeech.</li>'
                '<li><i class="fa fa-arrow-right"></i> Explanation mark (<i class="fa fa-exclamation" style="color:#D50000;"></i>) indicates that the file has been flagged.</li>'
                '<li><i class="fa fa-arrow-right"></i> A star mark (<i class="fa fa-star" style="color:grey;"></i>) the end of a batch - a good time to rest or switchtasks.</li>'
                '<li><i class="fa fa-arrow-right"></i> Question mark (<i class="fa fa-question" style="color:#007bff;"></i>) shows the current task.</li>'
                '<li><i class="fa fa-arrow-right"></i> Empty circle means that the task has not been annotated yet.</li>'
            '</ul>'
'<img src="/static/img/progress_bar.png" alt="Progress bar">'
            '<br>'
            '<b>Keyboard shortcuts:</b>'
            '<ul style="padding-left:2em">'
                '<li>&bull;  Play/Pause: Space bar</li>'
                '<li>&bull; Flag: F</li>'
                '<li>&bull; Instructions: I</li>'
            '</ul>'
]}

fgDict['2'] = {'annotationTag': ['Crowd', 'Noise', 'Unintelligible', 'Singing'], 'visualization': 'waveform', 'instructions': ["",
'In the fine grained annotation phase, you will be asked to label all parts of the audio where a specific kind of audio is heard. The annotation system will take you through different “passes”, each will ask you to identify different kinds of audio phenomenon. Passes are mostly independent, and you can expect to see the same file in different passes.'
            '<br><br>'
           ' <b><code>Crowd, Noise, Unintelligible, Singing Pass</code></b>'
            '<br>'
'Please mark parts of the audio that contain crowds, or any noise. Make sure to first select the right label, then annotate the regions. Note that annotated regions may overlap each other!<br>'
          '<ul style="padding-left:2em">'
               '<li><i class="fa fa-arrow-right"></i> <b>Noise: </b> any kind of noise: banging, engine sounds, wind, etc.</li>'
               '<li><i class="fa fa-arrow-right"></i> <b>Crowd: </b> crowd of people speaking. For example, at a party.</li>'
               '<li><i class="fa fa-arrow-right"></i> <b>Unintelligible: </b>  a person is speaking but is unintelligible (impossible to understand individual words), for example mumbling.</li>'
               '<li><i class="fa fa-arrow-right"></i> <b>Singing: </b> singing (regardless if from a live person, from TV, or recorded)</li>'
            '</ul>'

           '<br> <hr><hr>'
            '<b>Tool Overview</b>'
           '<ul style="padding-left:2em">'
                '<li><i class="fa fa-arrow-right"></i> Click the play button and listen to the recording.</li>'
                '<li><i class="fa fa-arrow-right"></i> Click and drag on the waveform visualization to create annotations.</li>'
                '<li><i class="fa fa-arrow-right"></i> To drag or resize a region, please first double click on it and make sure that the region is highlighted in green color. You can relisten/delete the region by clicking on the regions’ icons.</li>'
                '<li><i class="fa fa-arrow-right"></i> To delete a label, click on the cross mark located on the label.</li>'
                '<li><i class="fa fa-arrow-right"></i> Once done, click “SUBMIT AND LOAD NEXT RECORDING” to save the annotations and go to the next file.</li>'
                '<li><i class="fa fa-arrow-right"></i> If you are unclear about the file, please click the FLAG button, explain the reason and click submit.</li>'
                '<li><i class="fa fa-arrow-right"></i> Try to be precise when marking the start and end of audio annotations. Try to get within 100 milliseconds of the part (e.g., speech) beginning and ending.</li>'
                '<li><i class="fa fa-arrow-right"></i> You can change the visualization between the waveform (default) and spectrogram.</li>'
                '<li><i class="fa fa-arrow-right"></i> Undo and Redo buttons are available below the visualization</li>'
                '<li><i class="fa fa-arrow-right"></i> When annotating a part, do not forget to first select the right label, then annotate the regions. Note that annotated regions are allowed to overlap each other.</li>'
            '</ul><br>'
'<b>The progress bar on the bottom of the page shows an overview of the current batch:</b>'
            '<ul style="padding-left:2em">'
               ' <li><i class="fa fa-arrow-right"></i> Check mark (<i class="fa fa-check" style="color:#00C853;"></i>) indicates that the file has been labeled as speech.</li>'
                '<li><i class="fa fa-arrow-right"></i> Cross mark (<i class="fa fa-times" style="color:#007bff;"></i>) indicates that the file has been labeled as notspeech.</li>'
                '<li><i class="fa fa-arrow-right"></i> Explanation mark (<i class="fa fa-exclamation" style="color:#D50000;"></i>) indicates that the file has been flagged.</li>'
                '<li><i class="fa fa-arrow-right"></i> A star mark (<i class="fa fa-star" style="color:grey;"></i>) the end of a batch - a good time to rest or switchtasks.</li>'
                '<li><i class="fa fa-arrow-right"></i> Question mark (<i class="fa fa-question" style="color:#007bff;"></i>) shows the current task.</li>'
                '<li><i class="fa fa-arrow-right"></i> Empty circle means that the task has not been annotated yet.</li>'
            '</ul>'
'<img src="/static/img/progress_bar.png" alt="Progress bar">'
            '<br>'
            '<b>Keyboard shortcuts:</b>'
            '<ul style="padding-left:2em">'
                '<li>&bull;  Play/Pause: Space bar</li>'
                '<li>&bull; Flag: F</li>'
                '<li>&bull; Instructions: I</li>'
            '</ul>'
]}
fgDict['3'] = {'annotationTag': ['Person_B', 'Person_C', 'Others'], 'visualization': 'waveform', 'instructions': [
    "",
'In the fine grained annotation phase, you will be asked to label all parts of the audio where a specific kind of audio is heard. The annotation system will take you through different “passes”, each will ask you to identify different kinds of audio phenomenon. Passes are mostly independent, and you can expect to see the same file in different passes.'
            '<br><br>'
           ' <b><code>Source Pass</code></b>'
            '<br>'
'In this pass, help try to distinguish between speakers.<br>'
'<ul style="padding-left:2em">'
               '<li><i class="fa fa-arrow-right"></i> In this pass you will see parts of the audio have been previously annotated as speech. </li>'
               '<li><i class="fa fa-arrow-right"></i> If you hear more than one person talking, mark the part of speech spoken by the second speaker as <code>Person_B</code> . Unmarked speech is assumed to come from the first speaker, you do not need to mark it (there is no <code>Person_A</code> label)</li>'
               '<li><i class="fa fa-arrow-right"></i> The same if there is a third speaker (use <code>Percon_C</code> for the third speaker).</li>'
               '<li><i class="fa fa-arrow-right"></i> If there is only one person speaking, you do not need to mark anything!</li>'
               '<li><i class="fa fa-arrow-right"></i> If there are four or more speakers, try to distinguish between the main 3 <code>(persons A, B and C)</code>, and mark the rest as <code>Others</code></li>'
            '</ul>'

           '<br><hr><hr>'
            '<b>Tool Overview</b>'
           '<ul style="padding-left:2em">'
                '<li><i class="fa fa-arrow-right"></i> Click the play button and listen to the recording.</li>'
                '<li><i class="fa fa-arrow-right"></i> Click and drag on the waveform visualization to create annotations.</li>'
                '<li><i class="fa fa-arrow-right"></i> To drag or resize a region, please first double click on it and make sure that the region is highlighted in green color. You can relisten/delete the region by clicking on the regions’ icons.</li>'
                '<li><i class="fa fa-arrow-right"></i> To delete a label, click on the cross mark located on the label.</li>'
                '<li><i class="fa fa-arrow-right"></i> Once done, click “SUBMIT AND LOAD NEXT RECORDING” to save the annotations and go to the next file.</li>'
                '<li><i class="fa fa-arrow-right"></i> If you are unclear about the file, please click the FLAG button, explain the reason and click submit.</li>'
                '<li><i class="fa fa-arrow-right"></i> Try to be precise when marking the start and end of audio annotations. Try to get within 100 milliseconds of the part (e.g., speech) beginning and ending.</li>'
                '<li><i class="fa fa-arrow-right"></i> You can change the visualization between the waveform (default) and spectrogram.</li>'
                '<li><i class="fa fa-arrow-right"></i> Undo and Redo buttons are available below the visualization</li>'
                '<li><i class="fa fa-arrow-right"></i> When annotating a part, do not forget to first select the right label, then annotate the regions. Note that annotated regions are allowed to overlap each other.</li>'                
            '</ul><br>'
'<b>The progress bar on the bottom of the page shows an overview of the current batch:</b>'
            '<ul style="padding-left:2em">'
               ' <li><i class="fa fa-arrow-right"></i> Check mark (<i class="fa fa-check" style="color:#00C853;"></i>) indicates that the file has been labeled as speech.</li>'
                '<li><i class="fa fa-arrow-right"></i> Cross mark (<i class="fa fa-times" style="color:#007bff;"></i>) indicates that the file has been labeled as notspeech.</li>'
                '<li><i class="fa fa-arrow-right"></i> Explanation mark (<i class="fa fa-exclamation" style="color:#D50000;"></i>) indicates that the file has been flagged.</li>'
                '<li><i class="fa fa-arrow-right"></i> A star mark (<i class="fa fa-star" style="color:grey;"></i>) the end of a batch - a good time to rest or switchtasks.</li>'
                '<li><i class="fa fa-arrow-right"></i> Question mark (<i class="fa fa-question" style="color:#007bff;"></i>) shows the current task.</li>'
                '<li><i class="fa fa-arrow-right"></i> Empty circle means that the task has not been annotated yet.</li>'
            '</ul>'
'<img src="/static/img/progress_bar.png" alt="Progress bar">'
            '<br>'
            '<b>Keyboard shortcuts:</b>'
            '<ul style="padding-left:2em">'
                '<li>&bull;  Play/Pause: Space bar</li>'
                '<li>&bull; Flag: F</li>'
                '<li>&bull; Instructions: I</li>'
            '</ul>'
]}

CG_NUM_REPT = 2  # number of repetitions for each CGTask
CG_MIN_BATCH_SIZE = 1  # minimum batch size for CG
# CG_NUM_PASS = len(cgDict) # number of passes for FGTasks
CG_BATCH_SIZE = 10  # maximum batch size can be 10 because cg_test_intial size is 2 * 10

# FG_NUM_PASS = len(fgDict) # number of passes for FGTasks
FG_NUM_REPT = 2  # number of repetitions for each FGTask
FG_MIN_BATCH_SIZE = 1  # minimum batch size for FG
FG_BATCH_SIZE = 10  # maximum batch size can be 10 because fg_test_intial size is 2 * 10



# FILL THESE MANUALLY BY RUNNING cg_task_test() and fg_task_test()
# task_ids
cg_test_initial = [] #[1, 3, 5, 19, 21, 25, 27, 39, 41, 45, 47, 49, 63, 77, 89, 113, 115, 117, 119, 147, 169, 223, 225, 227, 229, 231, 233, 237, 239, 437, 439, 459, 461, 463, 465, 467, 469, 471, 483, 485]
# true labels (keys are cgsegment_ids)
cg_test_initial_true_labels = {} # {1: True, 2: True, 3: True, 10: False, 11: True, 13: False, 14: True, 20: True, 21: True, 23: False, 24: True, 25: True, 32: True, 39: False, 45: True, 57: False, 58: False, 59: False, 60: False, 74: True, 85: False, 112: True, 113: True, 114: True, 115: True, 116: False, 117: False, 119: True, 120: False, 219: False, 220: True, 230: True, 231: True, 232: True, 233: True, 234: True, 235: True, 236: True, 242: True, 243: False}
cg_test_batch_nums = len(cg_test_initial) // CG_BATCH_SIZE

fg_test_initial = [] #[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40]
fg_test_initial_true_labels = {} #{1: [(203, 160000)], 2: [(104, 235590)], 3: [(69, 54056), (56825, 128807)],
                            #    11: [(26640, 31637), (38737, 55831), (58066, 182063)],
                            #    14: [(33869, 44828), (58324, 72513), (75513, 93624), (94777, 105275), (107351, 132499),
                            #         (151417, 159839)],
                            #    20: [(300, 13797), (32946, 61439), (92932, 111965), (117618, 129154)],
                            #    21: [(13566, 26947), (52557, 69053), (95008, 133076), (136190, 159609)],
                            #    24: [(101814, 116464), (140805, 159839)],
                            #    25: [(89, 8657), (37612, 59033), (69669, 94340), (99954, 122852)],
                            #    32: [(121425, 157993)],
                            #    45: [(877, 47712), (57978, 74013), (79435, 108735), (129154, 142766), (146111, 159724)],
                            #    74: [(761, 24986), (27293, 49557), (51749, 66053), (74590, 100660), (106544, 120848),
                            #         (123270, 159609)],
                            #    112: [(69, 6875), (34446, 51403), (57286, 70668), (72744, 81627), (110581, 126731)],
                            #    113: [(107005, 125116), (157873, 160000)],
                            #    114: [(69, 20833), (66861, 77474), (85087, 89932), (96162, 114388), (118079, 129384)],
                            #    115: [(34561, 51288)],
                            #    119: [(28412, 35685), (39399, 61838), (62921, 71587), (73753, 85205)],
                            #    220: [(8606, 20372), (30523, 75974), (86818, 101929)],
                            #    230: [(646, 59132), (72167, 78050), (83818, 108043), (117041, 155109)],
                            #    232: [(19334, 38598), (39521, 52211), (57286, 95008), (107005, 113465),
                            #          (135844, 159608)],233: [(761, 8836), (35599, 48173), (58440, 72859), (85664, 122809)], 234: [(69, 14258), (25332, 39406), (87048, 130307), (136882, 157877)], 235: [(12758, 62247), (65707, 136998), (148072, 159724)], 236: [(69, 8490), (20949, 35484), (50249, 65938), (73782, 84395), (101814, 159724)], 242: [(24778, 47388)], 244: [(102045, 124539), (144035, 152225)], 251: [(55831, 75344), (91115, 123459)], 376: [(69, 11951), (16219, 25678), (39752, 159725)], 541: [(1338, 25448), (44828, 61901), (103083, 159723)], 553: [(5376, 28332), (47942, 59824), (72513, 109774), (118195, 141035), (146226, 159839)], 554: [(415, 30408), (36868, 47019), (53364, 69975), (81050, 93047), (105390, 117387), (147265, 159723)], 555: [(69, 25102), (32369, 56133), (76205, 159839)], 556: [(69, 11259), (37906, 56017), (133999, 159723)], 557: [(69, 16796), (102391, 117387), (126846, 147149)], 558: [(8952, 16796), (27409, 56479), (82319, 104813), (138151, 160000)], 740: [(69, 15412), (87279, 98930), (99622, 103660), (113926, 136652)], 741: [(25448, 51403), (71937, 85203), (91547, 99622), (104698, 128115)], 745: [(992, 11605), (28562, 38483), (47250, 71590), (78743, 101929), (132268, 139305), (156147, 159955)], 746: [(69, 21756)], 747: [(40790, 52211), (59247, 93278), (104813, 110812), (115311, 159724)]
                            #    }

# assert len(fg_test_initial) == len(cg_test_initial), 'Number of cg tests and fg tests should be the same!'
cg_test_batch_nums = len(cg_test_initial) // CG_BATCH_SIZE
fg_test_batch_nums = len(fg_test_initial) // FG_BATCH_SIZE
