#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

from jinja2 import Environment, Template

def dict_from_tuple( keys, data ):
    return dict( zip( keys, data ) )

def make_dict( key, data, f ):
    return dict( ( d[key], d ) for d in map( f, data ) )

def make_venue( data ):
    return dict_from_tuple( ['year', 'month', 'city', 'country'], data )

def make_conference( data ):
    d = dict_from_tuple( ['key', 'shortname', 'name', 'publisher', 'venues', 'type'], data + ('conf',) )
    d['venues'] = make_dict( 'year', d['venues'], make_venue )
    return d

def make_journal( data ):
    return dict_from_tuple( ['key', 'name', 'publisher', 'webpage'], data )

def make_author( data ):
    return dict_from_tuple( ['key', 'firstname', 'lastname'], data )

def make_university( data ):
    return dict_from_tuple( ['key', 'name', 'city', 'country', 'webpage', 'original_name'], data )

def make_conference_paper( data ):
    global conferences
    global authors

    d = dict_from_tuple( ['authors', 'conf', 'year', 'title', 'pages', 'doi'], data )
    d['authors'] = [authors[k] for k in d['authors']]
    d['conf'] = conferences[d['conf']]
    return d

def make_article( data ):
    global journals
    global authors

    d = dict_from_tuple( ['authors', 'journal', 'volume', 'number', 'year', 'title', 'pages', 'doi'], data )
    d['authors'] = [authors[k] for k in d['authors']]
    d['journal'] = journals[d['journal']]
    return d

def make_news( data ):
    global conferences
    global journals
    global confpapers
    global articles
    global authors

    if data[0] == 'tutorial':
        d = dict_from_tuple( ['type', 'name', 'url', 'introduction', 'authors', 'location'], data )
        d['authors'] = [authors[k] for k in d['authors']]
        d['conf'] = conferences[d['location'][0]]
        d['year'] = d['location'][1]
    else:
        d = dict_from_tuple( ['name', 'year'], data )

        if d['name'] in conferences:
            d['type'] = 'conf'
            d['papers'] = list( reversed( [p for p in confpapers if p['conf']['key'] == d['name'] and p['year'] == d['year']] ) )
        else:
            d['type'] = 'journal'
            d['papers'] = list( reversed( [a for a in articles if a['journal']['key'] == d['name'] and a['volume'] == d['year']] ) )

    return d

def make_filename( c, collection ):
    conf = c['conf']['key']
    year = c['year']

    same_venue = [c2 for c2 in collection if c2['conf']['key'] == conf and c2['year'] == year]

    if len( same_venue ) == 1:
        return "%s_%s" % ( year, conf )
    else:
        return "%s_%s_%d" % ( year, conf, same_venue.index( c ) + 1 )

def make_bibtex_title( title ):
    global capitalize, replacements

    for c in capitalize:
        title = title.replace( c, "{%s}" % c )
    for r, s in replacements:
        title = title.replace( r, s )
    return title

def format_bibtex_incollection( paper, collection, keyword ):
    global capitalize

    conf  = paper['conf']
    venue = conf['venues'][paper['year']]

    title = make_bibtex_title( paper['title'] )

    print( "@inproceedings{%s," % make_filename( paper, collection ) )
    print( "  author    = {%s},"     % " and ".join( "%s, %s" % ( a['lastname'], a['firstname'] ) for a in paper['authors'] ) )
    print( "  title     = {%s},"     % title )
    print( "  booktitle = {%s},"     % conf['name'] )
    print( "  year      = %d,"       % paper['year'] )
    print( "  month     = %s,"       % venue['month'] )
    print( "  address   = {%s, %s}," % ( venue['city'], venue['country'] ) )
    if paper['pages'] != "":
        print( "  pages     = {%s}," % paper['pages'] )
    if conf['publisher'] != "":
        print( "  publisher = {%s}," % conf['publisher'] )
    print( "  keywords  = {%s}"      % keyword )
    print( "}" )

def format_haml_incollection( paper, id ):
    global best_paper_data

    conf  = paper['conf']
    venue = conf['venues'][paper['year']]

    env = Environment()
    template = env.from_string('''
.item
  .pubmain
    .pubassets
      {{external}}
      %a.paper(href="papers/{{filename}}.pdf" data-toggle="tooltip" data-placement="top" title="View PDF")
        %span.glyphicon.glyphicon-cloud-download
    %a.paper(href="papers/{{filename}}.pdf" target="_blank")
      %img.pubthumb(src="images/{{image}}.png")
    %h4.pubtitle#c{{id}}
      {{title}}
    .pubauthor
      {{authors}}
    .pubcite
      %span.label.label-warning Conference Paper {{id}}
      In {{conf}} ({{shortname}}) | {{city}}, {{country}}, {{month}} {{year}}{{pages}} | Publisher: {{publisher}}{{best}}''')

    authors = ",\n      ".join( "%s %s" % ( a['firstname'], a['lastname'] ) for a in paper['authors'] )
    authors = authors.replace( "Ina Kodrasi", "%strong Ina Kodrasi" )

    filename = make_filename( paper, confpapers )
    image = "thumbs/" + filename if os.path.exists( "images/thumbs/%s.png" % filename ) else "nothumb"

    external = ""
    if paper['doi'] != "":
        external = "%%a(href=\"%s\" data-toggle=\"tooltip\" data-placement=\"top\" title=\"Open paper\" target=\"_blank\")\n        %%span.glyphicon.glyphicon-new-window" % paper['doi']

    besta = [b[1] for b in best_paper_data if b[0] == filename]
    if len( besta ) == 0:
        best = ""
    elif besta[0] == 'c':
        best = "\n    .pubcite(style=\"color: #990000\")\n      %%span.glyphicon.glyphicon-certificate\n      %b Best paper candidate"

    print( template.render( {'title': paper['title'],
                             'id': id,
                             'filename': filename,
                             'image': image,
                             'authors': authors,
                             'conf': conf['name'],
                             'shortname': conf['shortname'],
                             'city': venue['city'],
                             'country': venue['country'],
                             'month': monthnames[venue['month']],
                             'year': venue['year'],
                             'external': external,
                             'pages': " | Pages %s" % paper['pages'].replace( "--", "&ndash;" ) if paper['pages'] != "" else "",
                             'publisher': conf['publisher'],
                             'best': best} )[1:] )


def format_bibtex_article( paper ):
    global capitalize

    journal = paper["journal"]

    name = make_bibtex_title( journal["name"] )
    title = make_bibtex_title( paper['title'] )

    print( "@article{%s%d," % ( journal['key'], paper['year'] ) )
    print( "  author    = {%s},"     % " and ".join( "%s, %s" % ( a['lastname'], a['firstname'] ) for a in paper['authors'] ) )
    print( "  title     = {%s},"     % title )
    print( "  journal   = {%s},"     % name )
    if paper['volume'] == -1:
        print( "  note      = {in press}," )
    else:
        print( "  year      = %d,"       % paper['year'] )
        print( "  volume    = %d,"       % paper['volume'] )
        print( "  number    = {%s},"       % paper['number'] )
        if paper['pages'] != "":
            print( "  pages     = {%s}," % paper['pages'] )
    print( "  publisher = {%s},"     % journal['publisher'] )
    print( "  keywords  = {article}" )
    print( "}" )

def format_haml_article( paper, id ):
    journal = paper['journal']

    env = Environment()
    template = env.from_string('''
.item
  .pubmain
    .pubassets
      {{external}}
      /
        %a(href="papers/{{filename}}.pdf" data-toggle="tooltip" data-placement="top" title="View PDF")
          %span.glyphicon.glyphicon-cloud-download
    %a.paper(href="papers/{{filename}}.pdf" target="_blank")
      %img.pubthumb(src="images/{{image}}.png" border="0")
    %h4.pubtitle#j{{id}} {{title}}
    .pubauthor
      {{authors}}
    .pubcite
      %span.label.label-info Journal Article {{id}}
      In {{journal}} {{info}}{{pages}} | Publisher: {{publisher}}''')

    authors = ",\n      ".join( "%s %s" % ( a['firstname'], a['lastname'] ) for a in paper['authors'] )
    authors = authors.replace( "Ina Kodrasi", "%strong Ina Kodrasi" )

    number = "(%s)" % paper['number'] if paper['number'] != "" else ""

    filename = "%s_%s" % (paper['volume'], journal['key'])
    image = "thumbs/" + filename if os.path.exists( "images/thumbs/%s.png" % filename ) else "nothumb"

    external = ""
    if paper['doi'] != "":
        external += "%%a(href=\"%s\" data-toggle=\"tooltip\" data-placement=\"top\" title=\"Open paper\" target=\"_blank\")\n        %%span.glyphicon.glyphicon-new-window" % paper['doi']

    if os.path.exists("papers/%s.pdf" % filename):
        external += "\n      %%a.paper(href=\"papers/%s.pdf\" data-toggle=\"tooltip\" data-placement=\"top\" title=\"View PDF\")" \
                    "\n        %%span.glyphicon.glyphicon-cloud-download" % filename

    if paper['volume'] == -1:
        info = ""
    else:
        info = "%s%s, %s" % ( paper['volume'], number, paper['year'] )

    print( template.render( {'title': paper['title'],
                             'id': id,
                             'key': journal['key'],
                             'filename': filename,
                             'image': image,
                             'webpage': paper['journal']['webpage'],
                             'authors': authors,
                             'journal': paper['journal']['name'],
                             'info': info,
                             'pages': " | Pages %s" % paper['pages'].replace( "--", "&ndash;" ) if paper['pages'] != "" else "",
                             'external': external,
                             'publisher': journal['publisher']} )[1:] )

def format_haml_news( news ):
    print( "%li.list-group-item" )

    if news['type'] == "conf":
        papers = news['papers']

        if len( papers ) == 1:
            article = "  %%a(href=\"publications.html#c%i\") %s\n" % ( confpapers.index( papers[0] ) + 1, papers[0]["title"] )
        else:
            article = "  %ul\n"
            for p in papers:
                article += "    %%li\n      %%a(href=\"publications.html#c%i\") %s\n" % ( confpapers.index( p) + 1, p["title"] )
        print( "  The paper%s\n%s  %s been accepted at %s %d.\n  %%a.badge(href=\"publications.html#conferences\") publication" % ( "s" if len( papers ) > 1 else "", article, "have" if len( papers ) > 1 else "has", papers[0]["conf"]["shortname"], papers[0]["year"] ) )
    if news['type'] == "journal":
        papers = news['papers']

        if len( papers ) == 1:
            article = "  %%a(href=\"publications.html#j%i\") %s\n" % ( articles.index( papers[0] ) + 1, papers[0]["title"] )
        else:
            article = "  %ul\n"
            for p in papers:
                article += "    %%li\n      %%a(href=\"publications.html#j%i\") %s\n" % ( articles.index( p) + 1, p["title"] )
        print( "  The article%s\n%s  got accepted for publication in\n  %%i %s.\n  %%a.badge(href=\"publications.html\") publication" % ( "s" if len( papers ) > 1 else "", article, papers[0]["journal"]["name"] ) )
    if news['type'] == "tutorial":
        print( "  %s\n  %%a(href=\"%s\" target=\"_blank\") %s" % (news['introduction'], news['url'], news['name']) )
        if len( news['authors'] ) > 0:
            authors = ", ".join( "%s %s" % ( a['firstname'], a['lastname'] ) for a in news['authors'] )
            print( "  with %s" % authors )
        conf = news['conf']
        venue = conf['venues'][news['year']]
        print( "  in %s, %s at the %s %d conference.\n  %%a.badge(href=\"#\") tutorial" % (venue['city'], venue['country'], conf['shortname'], news['year']) )

def write_publications():
    global confpapers

    text = Template('''
\documentclass[conference]{IEEEtran}
\\usepackage[utf8]{inputenc}
\\usepackage[T1]{fontenc}

    \\usepackage[backend=biber,style=ieee]{biblatex}
\\addbibresource{publications.bib}

\\title{List of Publications}
\\author{
  \IEEEauthorblockN{Ina Kodrasi}
  \IEEEauthorblockA{Idiap, Switzerland}
}

\\begin{document}
  \\maketitle

  \\nocite{*}
  \printbibliography[type=book,title={Books}]
  \printbibliography[type=article,keyword=article,title={Journal articles}]
  \printbibliography[type=inproceedings,keyword=conference,title={Conference papers}]
\end{document}''')

    with open( "publications.tex", "w" ) as f:
        f.write( text.render().strip() + "\n" )

def format_haml_invited( invited ):
    template = Template('''
.pitem
  .pubmain(style="min-height:0px")
    {{ logo }}
    %h4.pubtitle {{ title }}
    .project-description
      Talk
      %i {{ talk_title }}
      {{ host }}
      ({{ month }}{{ year }})
    {{ more }}''')

    if invited['type'] == "uni":
        uni = invited['uni']
        title = uni['name']
        if uni['original_name'] != '':
            title += " (" + uni['original_name'] + ")"
        logo = '%%a(href="%s" target="_blank")\n      %%img.project-thumb(src="images/logos/%s.png" border="0")' % ( uni['webpage'], uni['key'] )
        host = 'invited by ' + invited['host']
    else:
        conf = invited['conf']
        title = conf['name'] + " " + str( invited['year'] )
        logo = ''
        host = ''

    if invited['webpage'] != '':
        more = '.project-description\n      %%a(href="%s" target="_blank") More information' % invited['webpage']
    else:
        more = ''

    talk_title = invited['title']
    month = monthnames[invited['month']] + " " if invited['month'] != '' else ''
    year = invited['year']

    print( template.render( title = title, logo = logo, talk_title = talk_title, host = host, month = month, year = year, more = more ) )


monthnames = {'jan': 'January', 'feb': 'February', 'mar': 'March', 'apr': 'April', 'may': 'May', 'jun': 'June', 'jul': 'July', 'aug': 'August', 'sep': 'September', 'oct': 'October', 'nov': 'November', 'dec': 'December'}
months = ["January", "Feburary", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
capitalize = []
replacements = []

conferences_data = [
    ( 'icassp', 'ICASSP', 'IEEE International Conference on Acoustics, Speech and Signal Processing', 'IEEE', [
        ( 2018, 'apr', 'Calgary, Alberta', 'Canada' ),
        ( 2017, 'mar', 'New Orleans, Louisiana', 'USA' ),
        ( 2016, 'mar', 'Shanghai', 'China' ),
        ( 2015, 'apr', 'Brisbane', 'Australia' ),
        ( 2014, 'may', 'Florence', 'Italy' ),
        ( 2013, 'may', 'Vancouver, British Columbia', 'Canada' ),
        ( 2012, 'mar', 'Kyoto', 'Japan' ),
        ( 2011, 'may', 'Prague', ' Czech Republic' )

    ] ),
    ( 'waspaa', 'WASPAA', 'IEEE Workshop on Applications of Signal Processing to Audio and Acoustics', 'IEEE', [
        ( 2017, 'oct', 'New Paltz, New York', 'USA' )
    ] ),
    ( 'chat', 'CHAT', 'International Workshop on Challenges in Hearing Assistive Technology', 'ISCA', [
        ( 2017, 'aug', 'Stockholm', 'Sweden' )
    ] ),
    ( 'hscma', 'HSCMA', 'Hands-free Speech Communication and Microphone Arrays', 'IEEE', [
        ( 2017, 'mar', 'San Francisco, California', 'USA' ),
    ] ),
    ( 'aes', 'AES', 'AES 60th Conference on Dereverberation and Reverberation of Audio, Music, and Speech', 'AES', [
        ( 2016, 'feb', 'Leuven', 'Belgium' )
    ] ),
    ( 'iwaenc', 'IWAENC', 'International Workshop on Acoustic Signal Enhancement', 'IEEE', [
        ( 2014, 'sep', 'Juan les Pins', 'France' ),
        ( 2012, 'sep', 'Aachen', 'Germany' )
    ] ),
    ( 'reverb', 'REVERB', 'REverberant Voice Enhancement and Recognition Benchmark challenge ', 'IEEE', [
        ( 2014, 'may', 'Florence', 'Italy' )
    ] ),
    ( 'eusipco', 'EUSIPCO', 'European Signal Processing Conference', 'EURASIP', [
        ( 2013, 'sep', 'Marrakech', 'Morocco' ),
        ( 2012, 'aug', 'Bucharest', 'Romania' )
    ] ),
    ( 'ieeei', 'IEEEI', 'IEEE Convention of Electrical and Electronics Engineers in Israel', 'IEEE', [
        ( 2012, 'nov', 'Eilat', 'Israel' )
    ] ),
    ( 'euronoise', 'EuroNoise', 'European Congress and Exposition on Noise Control Engineering', 'EAA', [
        ( 2018, 'may', 'Crete', 'Greece' )
    ] ),
    ( 'interspeech', 'IS', 'Interspeech', 'ISCA', [
        ( 2018, 'sep', 'Hyderabad', 'India' )
    ]),
        ( 'itg', 'ITG', 'ITG Conference on Speech Communication', 'VDE', [
        ( 2018, 'oct', 'Oldenburg', 'Germany' )
        ]),
    ( 'ofdm', 'OFDM', 'International OFDM Workshop', '', [
        ( 2009, 'sep', 'Hamburg', 'Germany' )
    ]),
    ( 'spie', 'SPIE', 'Proceedings of SPIE - The International Society for Optical Engineering', '', [
        ( 2008, 'apr', 'California', 'USA' )
    ])
]
      

journals_data = [
    ( 'itaslp', 'IEEE/ACM Transactions on Audio, Speech and Language Processing', 'IEEE', 'https://signalprocessingsociety.org/publications-resources/ieeeacm-transactions-audio-speech-and-language-processing/ieeeacm' ),
    ( 'eurasip', 'EURASIP Journal on Advances in Signal Processing', 'Springer', 'https://asp-eurasipjournals.springeropen.com/' ),
    ( 'jaes', 'Journal of the Audio Engineering Society', 'AES', 'http://www.aes.org/journal/' )
]

authors_data = [
    ( 'ab', 'Alexander', 'Burenkov' ),
    ( 'ae', 'Andreas', 'Erdmann' ),
    ( 'aj', 'Ante', 'Jukic' ),
    ( 'am', 'Alfred', 'Mertins' ),
    ( 'aw', 'Anna', 'Warzybok' ),
    ( 'bc', 'Benjamin', 'Cauchi' ),
    ( 'bk', 'Birger', 'Kollmeier' ),
    ( 'ck', 'Christian', 'Kampen' ),
    ( 'dm', 'Daniel', 'Marquardt' ),
    ( 'eg', 'Eleftheria', 'Georganti' ),
    ( 'eh', 'Emanuel', 'Habets' ),
    ( 'fh', 'Fanging', 'Hu' ),
    ( 'gc', 'Gilles', 'Curtois' ),
    ( 'hb', 'Herve', 'Bourlard' ),
    ( 'hl', 'Herve', 'Lissek' ),
    ( 'ik', 'Ina', 'Kodrasi' ),
    ( 'jj', 'Jan', 'Jungmann' ),
    ( 'jr', 'Jan', 'Rennies' ),
    ( 'mt', 'Marvin', 'Tammen' ),
    ( 'rr', 'Robert', 'Rehr' ),
    ( 'sd', 'Simon', 'Doclo' ),
    ( 'sg', 'Stefan', 'Goetze' ),
    ( 'sgl', 'Stefan', 'Gerlach' ),
    ( 'tf', 'Tim', 'Fuhner' ),
    ( 'tg', 'Timo', 'Gerkmann' ),
    ( 'vg', 'Vincent', 'Grimaldi' ),
    ( 'wh', 'Werner', 'Henkel' )
    
    

]

confpapers_data = [
    ( ['tf', 'ck', 'ik', 'ab', 'ae'],  'spie', 2008, 'A simulation study on the impact of lithographic process variations on CMOS device performance', '', '' ),
    ( ['wh', 'fh', 'ik'],  'ofdm',   2009, 'Inherent time-frequency coding in OFDM -- a Possibility for ISI correction without a cyclic prefix?', '', '' ),
    ( ['ik', 'sd'],  'icassp',   2011, 'Microphone position optimization for planar superdirective beamforming', '109--112', '' ),
    ( ['ik', 'sd'],  'icassp',   2012, 'Robust partial multichannel equalization techniques for speech dereverberation', '537--540', '' ),
    ( ['ik', 'sd'],  'eusipco',   2012, 'The effect of inverse filter length on the robustness of acoustic multichannel equalization', '2442--2446', '' ),
    ( ['ik', 'sg', 'sd'],  'iwaenc',   2012, 'Increasing the robustness of acoustic multichannel equalization by means of regularization', '161--164', '' ),
    ( ['ik', 'sg', 'sd'],  'ieeei',   2012, 'Non-intrusive regularization for least-squares multichannel equalization techniques for speech dereverberation', '', '' ),
    ( ['ik', 'sg', 'sd'],  'icassp', 2013, 'A perceptually constrained channel shortening technique for speech dereverberation', '151--155', '' ),
    ( ['ik', 'sd'],  'eusipco',   2013, 'Regularized subspace-based acoustic multichannel equalization for speech dereverberation', '', '' ),
    ( ['ik', 'tg', 'sd'],  'icassp',   2014, 'Frequency-domain single-channel inverse filtering for speech dereverberation: Theory and practice', '5214-5218', '' ),
    ( ['bc', 'ik', 'rr', 'sgl', 'aj', 'tg', 'sd', 'sg'],  'reverb',   2014, 'Joint dereverberation and noise reduction using beamforming and a single-channel speech enhancement scheme', '', '' ),
    ( ['aw', 'ik', 'jj', 'eh', 'tg', 'am', 'sd', 'bk', 'sg'],  'iwaenc',   2014, 'Subjective speech quality and speech intelligibility evaluation of single-channel dereverberation algorithms', '333--337', '' ),
    ( ['sg', 'aw', 'ik', 'jj', 'bc', 'jr', 'eh', 'am', 'tg', 'sd', 'bk'],  'iwaenc',   2014, 'A study on speech quality and speech intelligibility measures for quality assessment of single-channel dereverberation algorithms', '234--238', '' ),
    ( ['ik', 'sd'],  'iwaenc',   2014, 'Joint dereverberation and noise reduction based on acoustic multichannel equalization', '140--144', '' ),
    ( ['ik', 'dm', 'sd'],  'icassp',   2015, 'Curvature based optimization of the trade-off parameter in the speech distortion weighted multichannel Wiener filter', '315-319', '' ),
    ( ['ik', 'sd'],  'aes',   2016, 'Incorporating the noise statistics in acoustic multi-channel equalization', '', '' ),
    ( ['ik', 'aj', 'sd'],  'icassp',   2016, 'Robust sparsity-promoting acoustic multi-channel equalization for speech dereverberation', '166--170', '' ),
    ( ['ik', 'sd'],  'hscma',   2017, 'EVD-based multi-channel dereverberation of a moving speaker using different RETF estimation methods', '116--120', '' ),
    ( ['ik', 'sd'],  'icassp',   2017, 'Late reverberant power spectral density estimation based on an eigenvalue decomposition', '611--615', '' ),
    ( ['ik', 'dm', 'sd'],  'chat',   2017, 'A simulation study on binaural dereverberation and noise reduction based on diffuse power spectral density sstimators', '', '' ),
    ( ['ik', 'sd'],  'waspaa',   2017, 'Multi-channel late reverberation power spectral density estimation based on nuclear norm minimization', '101--105', '' ),
    ( ['mt', 'ik', 'sd'],  'icassp',   2018, 'Complexity reduction of eigenvalue decomposition-based diffuse power spectral density estimators using the power method', '451--455', '' ),
    ( ['ik', 'sd'],  'icassp',   2018, 'Joint late reverberation and noise power spectral density estimation in a spatially homogeneous noise field', '441--445', '' ),
    ( ['gc', 'vg', 'hl', 'ik', 'eg'],  'euronoise',   2018, 'Experimental evaluation of speech enhancement methods in remote microphone systems for hearing aids', '351--358', '' ),
    ( ['ik', 'hb'],  'interspeech',  2018, 'Single-channel late reverberation power spectral density estimation using denoising autoencoders', '', '' ),
    ( ['mt', 'ik', 'sd'],  'itg',  2018, 'Joint estimation of relative early transfer function vector and diffuse power spectral density estimation using an alternating least-squares approach', '', '' ),
    ( ['ik', 'hb'],  'itg',  2018, 'Statistical modeling of speech spectral coefficients in patients with Parkinson’s disease', '', '' ),
]

article_data = [
    
    ( ['ik', 'sg', 'sd'], 'itaslp', 21, "9", 2013, 'Regularization for partial multichannel equalization for speech dereverberation', '1879--1890', '' ),
    ( ['bc', 'ik', 'rr', 'sgl', 'aj', 'tg', 'sd', 'sg'], 'eurasip', 61, "", 2015, 'Combination of MVDR beamforming and single-channel spectral processing for enhancing noisy and reverberant speech', '', '' ),
    ( ['ik', 'sd'], 'itaslp', 24, "4", 2016, ' Joint Dereverberation and noise reduction based on acoustic multichannel equalization', '680--693', '' ),
    ( ['ik', 'bc', 'sg', 'sd'], 'jaes', 65, "1/2", 2017, 'Instrumental and perceptual evaluation of dereverberation techniques based on robust acoustic multi-channel equalization', '117--129', '' ),
    ( ['ik', 'sd'], 'itaslp', 25, "7", 2017, ' Signal-dependent penalty functions for robust acoustic multi-channel equalization', '1512--1525', '' ),
    ( ['ik', 'sd'], 'eurasip', 11, "", 2018, ' Improving the conditioning of the optimization criterion in acoustic multi-channel equalization using shorter reshaping filters', '', '' ),
    ( ['ik', 'sd'], 'itaslp', 26, "6", 2018, '  Analysis of eigenvalue decomposition-based late reverberation power spectral density estimation', '1106--1118', '' )
]

best_paper_data = [ ( '2016_date_1', 'c' ), ( '2016_sat', 'c' ) ]

news_data = [
    ( 'icassp', 2018 ),
    ( 'eurasip', 11),
    ( 'itaslp', 26),
    ( 'euronoise', 2018 ),
    ( 'interspeech', 2018),
    ( 'itg', 2018),
    
]

authors = make_dict( 'key', authors_data, make_author )
conferences = make_dict( 'key', conferences_data, make_conference )
journals = make_dict( 'key', journals_data, make_journal )

confpapers = list( map( make_conference_paper, confpapers_data ) )
articles = list( map( make_article, article_data ) )

news = list( map( make_news, news_data ) )

def cmd_publications():
    for key, conf in conferences.items():
        if len( conf['shortname'] ) > 0:
            print( "@STRING{%s = {%s}}" % ( conf['shortname'], conf['name'] ) )
    print()

    print( "@book{book1," )
    print( "  author    = {Ina Kodrasi}," )
    print( "  title     = {Dereverberation and Noise Reduction Techniques based on Acoustic Multi-Channel Equalization}," )
    print( "  publisher = {Doktorhut}," )
    print( "  year      = 2015" )
    print( "}" )
    print()

    for a in articles:
        format_bibtex_article( a )
        print()

    for c in confpapers:
        format_bibtex_incollection( c, confpapers, "conference" )
        print()

    write_publications()

def cmd_haml():
    year = ""
    for index, c in enumerate( reversed( confpapers ) ):
        if c['year'] != year:
            year = c['year']
            print( "%%h4 %s" % year )
        format_haml_incollection( c, len( confpapers ) - index )

def cmd_haml_article():
    year = ""
    for index, c in enumerate( reversed( articles ) ):
        if c['year'] != year:
            year = c['year']
            print( "%%h4 %s" % ( "In press" if year == 0 else year ) )
        format_haml_article( c, len( articles ) - index )

def cmd_haml_news():
    for n in reversed( news ):
        format_haml_news( n )

def cmd_stats():
    num_countries = len( set( [p['conf']['venues'][p['year']]['country'] for p in confpapers] ) )
    print( "%d authors, %d conference papers, in %d countries" % ( len( authors ), len( confpapers ), num_countries ) )

def cmd_pdfs():
    for c in confpapers:
        filename = make_filename( c, confpapers )

        if os.path.exists( "papers/%s.pdf" % filename ):
            if not os.path.exists( "images/thumbs/%s.png" % filename ):
                print( "[i] creating thumbnail for \"%s\" (%s %d)" % ( c['title'], c['conf']['shortname'], c['year'] ) )
                os.system( "convert papers/%s.pdf /tmp/%s.png" % ( filename, filename ) )
                os.system( "convert -trim -resize x130 /tmp/%s-0.png images/thumbs/%s.png" % ( filename, filename ) )
        else:
            print( "[w] no PDF for \"%s\" (%s %d)" % ( c['title'], c['conf']['shortname'], c['year'] ) )

    for a in articles:
        filename = "%s_%s" % (a['volume'], a['journal']['key'])

        if os.path.exists( "papers/%s.pdf" % filename ):
            if not os.path.exists( "images/thumbs/%s.png" % filename ):
                print( "[i] creating thumbnail for \"%s\" (%s %d)" % ( a['title'], a['journal']['name'], a['volume'] ) )
                os.system( "convert papers/%s.pdf /tmp/%s.png" % ( filename, filename ) )
                os.system( "convert -trim -resize x130 /tmp/%s-0.png images/thumbs/%s.png" % ( filename, filename ) )
        else:
            print( "[w] no PDF for \"%s\" (%s %d)" % ( a['title'], a['journal']['name'], a['volume'] ) )
            

def cmd_geo():
    from geopy.geocoders import Nominatim
    locator = Nominatim()
    for k1, d in conferences.items():
        for k2, v in d['venues'].items():
            location = "%s, %s" % (v['city'], v['country'])
            l = locator.geocode( location )
            if l:
                print( "  {title: '%s', position: {lat: %s, lng: %s}}," % (location, l.latitude, l.longitude) )
            else:
                print( "No geocode for %s" % v )

if len( sys.argv ) == 2:
    globals()['cmd_%s' % sys.argv[1]]()
