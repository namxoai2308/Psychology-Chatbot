% -------------------------------------------------------------------
%  @LaTeX-class-file{
%     filename        = "hust-thesis.cls",
%     version         = "0.0.1",
%     date            = "2021",
%     codetable       = "ISO/ASCII",
%     keywords        = "LaTeX, hust-thesis",
%     supported       = "send email to ngocjr7@gmail.com",
%     docstring       = "A thesis class for a HUST dissertation. This is an adaptation based on Harvard's template."
% --------------------------------------------------------------------

\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{uet-awesome-thesis}[2021/12/28 University of Engineering and Technology Thesis Class]

\newcommand{\mylanguage}{en}

\DeclareOption{en}{\renewcommand{\mylanguage}{en}}
\DeclareOption{vi}{\renewcommand{\mylanguage}{vi}}
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{book}}
\ProcessOptions\relax
\LoadClass[oneside]{book}
\usepackage{scrextend}
\changefontsizes{13pt}

% Required packages
\RequirePackage{graphicx}
\RequirePackage{xstring}
\RequirePackage{hyperref}
\RequirePackage[toc]{glossaries}
\RequirePackage{glossary-mcols}
\RequirePackage{here}
\RequirePackage[toc]{appendix}

\RequirePackage{amssymb}
\RequirePackage{amsmath}
\RequirePackage{mathtools}
\RequirePackage{mathspec} %loads fontspec as well

\RequirePackage[numbers, comma, sort&compress]{natbib}
\RequirePackage[small, md, sc]{titlesec}
\RequirePackage[tight,nice]{units}
\RequirePackage{verbatim}
\RequirePackage[palatino]{quotchap}
\RequirePackage{ragged2e}
% colors
\RequirePackage{color}
\definecolor{Crimson}{rgb}{0.6471, 0.1098, 0.1882}

\hypersetup{
	linktocpage,
    colorlinks,
    citecolor=black,
    filecolor=black,
    linkcolor=black,
    urlcolor=black,
}

\RequirePackage{url}
\RequirePackage[titles]{tocloft}

\setcounter{tocdepth}{3}
\setcounter{secnumdepth}{3}

\renewcommand{\cftchapfont}{\normalsize \scshape}
\setlength{\parindent}{1cm}
\setlength{\parskip}{6pt}

\RequirePackage{pdfsync} %do pdf synchronization [andy]
\RequirePackage[
    type={CC},
    modifier={by-nc-sa},
    version={3.0},
]{doclicense}

% \usepackage[closeFloats, noSeparatorLine]{fltpage} %use the custom modified fltpage package
% \RequirePackage{afterpage} 

\synctex=1 % turn synctex on automatically to sync between pdf viewer [andy]

%   list an entire bibliography entry inline. Useful for acknowledging when my paper was previously published
\RequirePackage{bibentry} 
\nobibliography*        

% \RequirePackage{lettrine} % big letter at start of chapter
\RequirePackage[a4paper]{geometry}
\geometry{left=3cm, right=2cm, top=2.5cm, bottom=3cm}

\RequirePackage{fancyhdr} 
\pagestyle{plain} % options: empty , plain , fancy

% \RequirePackage[palatino]{quotchap} % chaper number 
% \definecolor{chaptergrey}{rgb}{0.6,0,0}

\RequirePackage{afterpage} 


\RequirePackage{titling}
\RequirePackage{setspace} 
\RequirePackage{booktabs} % for much better looking tables
\RequirePackage[labelfont={bf},justification=RaggedRight,margin=0pt, figurewithin=section, tablewithin=section]{caption}

% line alignment
\linespread{1.08333333}
\addtolength{\footnotesep}{\footnotesep}
\justifying
%\raggedright


\titleformat{\chapter}[display]
  {\Huge}
  {\chaptertitlename\ \thechapter}{20pt}{\Huge\sloppy}

\titleformat{\section}
  {\Large}
  {\thesection}{1em}{\Large}
  
\titleformat{\subsection}
  {\large}
  {\thesubsection}{1em}{\large}

\titleformat{\subsubsection}[runin]
  {\bfseries}
  {\thesubsubsection}{1em}{}

\titleformat{\paragraph}[runin]
  {\it}
  {}{1em}{}

% some definitions
\def\degreeyear#1{\gdef\@degreeyear{#1}}
\def\degreemonth#1{\gdef\@degreemonth{#1}}
\def\advisor#1{\gdef\@advisor{#1}}
% Vietnamese pages: show TS. instead of Ph.D in advisor name (after full preamble).
\newcommand{\AdvisorVI}{}
\AtBeginDocument{%
	\begingroup
	\StrSubstitute{\@advisor}{Ph.D.}{TS.}[\uet@advtmp]%
	\StrSubstitute{\uet@advtmp}{Ph.D}{TS.}[\uet@advtmp]%
	\edef\x{\endgroup\def\noexpand\AdvisorVI{\uet@advtmp}}%
	\x
}
\def\university#1{\gdef\@university{#1}}
\def\universitycity#1{\gdef\@universitycity{#1}}
\def\major#1{\gdef\@major{#1}}

% Vietnamese mirror of the English side cover (page 3 when \documentclass[en]{...}).
\let\viet@title\relax
\let\viet@university\relax
\let\viet@major\relax
\def\viettitle#1{\gdef\viet@title{#1}}
\def\vietuniversity#1{\gdef\viet@university{#1}}
\def\vietmajor#1{\gdef\viet@major{#1}}

\newcommand{\isenglish}[3][\mylanguage]{
    \ifthenelse{\equal{#1}{en}}{#2}{#3}
}

\isenglish{
    \RequirePackage[english,vietnamese,main=english]{babel}
}{
    \RequirePackage[vietnamese,english,main=vietnamese]{babel}
}

\RequirePackage{tikz}
\usetikzlibrary{calc}
\usetikzlibrary{decorations.pathmorphing}

% Cover TikZ inner frame is inset 2.4cm each side; keep title well inside (not \textwidth).
\newcommand{\uet@covertitlefrom}[1]{%
	\parbox{\dimexpr\paperwidth-4.8cm-1.8cm\relax}{%
		\centering\sloppy\emergencystretch=4em\relax
		\fontsize{17pt}{21pt}\selectfont
		\textbf{\MakeUppercase{#1}}%
		\par
	}%
}
\newcommand{\uet@covertitle}{\uet@covertitlefrom{\@title}}
% Vietnamese degree line: forced single line, scaled down if needed to stay inside frame.
\newcommand{\uet@coverthesistypevi}{%
	\resizebox{\dimexpr\paperwidth-4.8cm-1.8cm\relax}{!}{%
		\fontsize{15pt}{18pt}\selectfont
		\textbf{KHÓA LUẬN TỐT NGHIỆP ĐẠI HỌC HỆ CHÍNH QUY}%
	}%
}

\renewcommand{\maketitle}{ 
	\singlespacing
	\thispagestyle{empty}
% 	\vspace*{\fill} 
    % \vspace{150pt} 
    \begin{tikzpicture}[overlay,remember picture]
    \draw [line width=1.5mm]
        ($ (current page.north west) + (2.2cm,-2.2cm) $)
        rectangle
        ($ (current page.south east) + (-2.2cm,2.2cm) $);
    \draw [line width=0.5mm]
        ($ (current page.north west) + (2.4cm,-2.4cm) $)
        rectangle
        ($ (current page.south east) + (-2.4cm,2.4cm) $);
    \end{tikzpicture}
    
	\begin{center}
    \begin{large}\fontsize{12pt}{1}\selectfont \textbf{\MakeUppercase{\@university}} \end{large} \\[1cm]
    {\includegraphics[scale=0.07]{UET_logo.png} \\ [1cm]}
    {\fontsize{14pt}{1}\selectfont \textbf{\@author}}\\[2cm]
    \uet@covertitle\\[4cm]
    
    {\fontsize{15pt}{1}\selectfont \textbf{\isenglish{BACHELOR THESIS}{KHÓA LUẬN TỐT NGHIỆP ĐẠI HỌC HỆ CHÍNH QUY}}}\\[0.3cm]
    {\fontsize{15pt}{1}\selectfont \textbf{\isenglish{Major}{Ngành}: \@major}}\\[3.5cm]
    
    \vspace*{\fill}
	{\fontsize{12pt}{1}\selectfont \textbf{\@universitycity, \@degreeyear}}\\
	
	\end{center} 
	\newpage
}

\newcommand{\makesidecover}{ 
	\singlespacing
	\thispagestyle{empty}
% 	\vspace*{\fill} 
    % \vspace{150pt} 
    \begin{tikzpicture}[overlay,remember picture]
    \draw [line width=1.5mm]
        ($ (current page.north west) + (2.2cm,-2.2cm) $)
        rectangle
        ($ (current page.south east) + (-2.2cm,2.2cm) $);
    \draw [line width=0.5mm]
        ($ (current page.north west) + (2.4cm,-2.4cm) $)
        rectangle
        ($ (current page.south east) + (-2.4cm,2.4cm) $);
    \end{tikzpicture}
	\begin{center}
    \begin{large}\fontsize{12pt}{1}\selectfont \textbf{\MakeUppercase{\@university}} \end{large} \\[2cm]
    {\fontsize{14pt}{1}\selectfont \textbf{\@author}}\\[2.5cm]
    \uet@covertitle\\[4cm]
    
    {\fontsize{15pt}{1}\selectfont \textbf{\isenglish{BACHELOR THESIS}{KHÓA LUẬN TỐT NGHIỆP ĐẠI HỌC HỆ CHÍNH QUY}}}\\[0.3cm]
    {\fontsize{15pt}{1}\selectfont \textbf{\isenglish{Major}{Ngành}: \@major}}\\[3cm]
	
	\end{center} 
    
    {\noindent \fontsize{14pt}{1}\selectfont \textbf{\isenglish{Supervisor: \@advisor}{Cán bộ hướng dẫn: \AdvisorVI}}}\\[2.5cm]
    
    \vspace*{\fill}
    
    \begin{center}
	{\fontsize{12pt}{1}\selectfont \textbf{\@universitycity, \@degreeyear}}\\
	\end{center}
	\newpage
}

% Same layout as \makesidecover but Vietnamese labels and optional
% \vietuniversity / \viettitle / \vietmajor (fallback: English metadata).
\newcommand{\makesidecovervietnamese}{%
	\singlespacing
	\thispagestyle{empty}
    \begin{tikzpicture}[overlay,remember picture]
    \draw [line width=1.5mm]
        ($ (current page.north west) + (2.2cm,-2.2cm) $)
        rectangle
        ($ (current page.south east) + (-2.2cm,2.2cm) $);
    \draw [line width=0.5mm]
        ($ (current page.north west) + (2.4cm,-2.4cm) $)
        rectangle
        ($ (current page.south east) + (-2.4cm,2.4cm) $);
    \end{tikzpicture}
	\begin{otherlanguage}{vietnamese}
	\begingroup
	\ifx\viet@university\relax\else\let\@university\viet@university\fi
	\ifx\viet@title\relax\else\let\@title\viet@title\fi
	\ifx\viet@major\relax\else\let\@major\viet@major\fi
	\begin{center}
    \begin{large}\fontsize{12pt}{1}\selectfont \textbf{\MakeUppercase{\@university}} \end{large} \\[2cm]
    {\fontsize{14pt}{1}\selectfont \textbf{\@author}}\\[2.5cm]
    \uet@covertitle\\[4cm]
    \uet@coverthesistypevi\\[0.3cm]
    {\fontsize{15pt}{1}\selectfont \textbf{Ngành: \@major}}\\[3cm]
	\end{center}
    {\noindent \fontsize{14pt}{1}\selectfont \textbf{Cán bộ hướng dẫn: \AdvisorVI}}\\[2.5cm]
    \vspace*{\fill}
    \begin{center}
	{\fontsize{12pt}{1}\selectfont \textbf{\@universitycity, \@degreeyear}}\\
	\end{center}
	\endgroup
	\end{otherlanguage}
	\newpage
}

\def\authorclass#1{\gdef\@authorclass{#1}}
\def\duration#1{\gdef\@duration{#1}}
\def\statement#1{\gdef\@statement{#1}}
\def\declaration#1{\gdef\@declaration{#1}}

% You might also consider licensing your work under Creative Commons). See: http://creativecommons.org/weblog/entry/12824 for other PhD students who have released their work under creative commons.

\newcommand{\abstractpage}[2][\mylanguage]{
	\newpage
% 	\pagenumbering{roman}
% 	\setcounter{page}{3}
	\pagestyle{fancy}
	\lhead{\isenglish[#1]{Thesis advisor: \@advisor}{Giảng viên hướng dẫn: \AdvisorVI}} \rhead{\@author}
	\renewcommand{\headrulewidth}{0.0pt} 
	\begin{center}
	\vspace*{1pt}
	{\LARGE \bf \isenglish[#1]{Abstract}{Tóm tắt đồ án}} \\ \rm
	\end{center}
	\doublespace %Harvard registrar requests that abstract is double spaced
	#2
	\doublespace %Harvard registrar requests that abstract is double spaced	
	\newpage \lhead{} \rhead{}
	\cfoot{\thepage}
	\onehalfspacing
}

\newcommand{\dedicationpage}[1]{
	\pagestyle{fancy}
	\newpage \thispagestyle{fancy} \vspace*{\fill}
	\sc \noindent #1
	\vspace*{\fill} \newpage \rm
	}

% the list of authors
\newcommand{\authorlist}[1]{
	\pagestyle{fancy}
	\newpage
	\thispagestyle{fancy} 
	\isenglish{\chapter*{Author List}}{\chapter*{Danh sách tác giả}}
	\noindent #1
	\newpage \rm
	}
	

% the acknowledgments page
\newcommand{\acknowledgments}[1]{
    \isenglish{\chapter*{Acknowledgments}}{\chapter*{Lời cảm ơn}}
    \pagestyle{fancy}
	\noindent
	\onehalfspacing
	#1
	\vspace*{\fill} 
	\newpage
}

\newcommand{\authorship}{
    \isenglish{\chapter*{Authorship}}{\chapter*{Tuyên thệ của tác giả}}
    \pagestyle{fancy}
	\noindent I hereby declare that the thesis is my own original work, conducted under the
supervision of Ph.D. Tran Van Khanh.
All references to related research have been clearly cited in the bibliography. This
	thesis does not contain any material copied from others’ works without proper
acknowledgment. \\ [2cm]

    \noindent Signature:......................................................
	\vspace*{\fill} 
	\newpage
}

\newcommand{\approval}{
    \isenglish{\chapter*{Supervisor's approval}}{\chapter*{Xác nhận của cán bộ hướng dẫn}}
    \pagestyle{fancy}
	\noindent “I hereby approve that the thesis in its current form is ready for committee examination as a requirement for the Artificial Intelligence degree at the University of Engineering and Technology.” \\ [2cm]

    \noindent Signature:......................................................
	\vspace*{\fill} 
	\newpage
}
	
% An environment for paragraph-style section
\providecommand\newthought[1]{%
   \addvspace{1.0\baselineskip plus 0.5ex minus 0.2ex}%
   \noindent\textsc{#1}}

% An environment for sign box
\newcommand{\signbox}[2]{
\begin{minipage}{0.5\linewidth}
\end{minipage}\hfill
\begin{minipage}{0.45\linewidth}
\begin{flushright}
\vbox{
    \begin{center}
	\textit{\@universitycity, \isenglish{date}{ngày} \space \space \space \isenglish{month}{tháng} \space \space \space \isenglish{year}{năm} \@degreeyear}
	\\ #1
	\\~
	\\~
	\\ \textit{#2}
	\end{center}
}
\end{flushright}
\end{minipage}
}

% \dotline and \dotfill
\def\dotfill#1{\cleaders\hbox to #1{.}\hfill}
\newcommand\dotline[2][.5em]{\leavevmode\hbox to #2{\dotfill{#1}\hfil}}

\renewenvironment{savequote}[1][10cm]{%
\begin{lrbox}{\@quotebox}
\noindent
\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}lr|}
&\begin{minipage}[t]{#1}\footnotesize\quotefont
\ignorespaces
}{%
\end{minipage}
\end{tabular*}
\end{lrbox}
\global\setbox\@quotebox\copy\@quotebox
\global\let\@printcites\@iprintcites
\ignorespacesafterend}


% remove hyperlink, mostly used for citation in caption and headline
\newcommand{\nohyper}[1]{\protect\NoHyper#1\protect\endNoHyper}

\renewcommand\bibname{References}
\renewcommand\listfigurename{Listing of Figures}

% undo the wrong changes made by mathspec
\makeatletter 
\let\RequirePackage\original@RequirePackage
\let\usepackage\RequirePackage
\makeatother
