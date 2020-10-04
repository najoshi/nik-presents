#!/usr/bin/perl

use Text::Wrap;

my $firstfile=1;

my $text_color = "white";
my $text_font = "helvetica 20 bold";
my $location="";
my $title="";
my $text="";
my $subtitles="";
my %extra_text=();
my $oa="N";
my $outfile;
my $outfd;


sub get_extra_text {
	my ($path) = @_;
	my $usedir;

	if (-f $path && !%extra_text) {
		($usedir) = $path =~ /^(.+)\//;
	} else {
		$usedir = $path;
	}

        if (-e "$usedir/extra_text.txt") {
# print STDERR "inside get extra: $usedir\n";
               %extra_text=();
               open ($et, "<$usedir/extra_text.txt");
               while ($fn=<$et>) {
                     chomp $fn;
                     $text = <$et>;
                     chomp $text;

                     if ($text eq "") {next;}

                     $text =~ s/\"/\\\"/g;
                     $extra_text{$fn} = $text;
                }
                close ($et);
         }

# foreach $item (keys %extra_text) {
#	print "$item: $extra_text{$item}\n";
# }
}


sub process_dir {
	my ($thedir) = @_;
	my $i;
	my @thefiles;

	opendir (DIR, $thedir);
	@thefiles = sort readdir (DIR);
	closedir (DIR);

	get_extra_text($thedir);

	for ($i=0; $i<=$#thefiles; $i++) {
		if ($thefiles[$i] !~ /^\.+/) {
			process_file ($thedir . "/" . $thefiles[$i]);
		}
	}

	%extra_text=();
}


sub process_image {
    my ($thefile, $isincurrdir, $ext) = @_;

    ($trip_text,$title) = $thefile =~ /^.+?\/(.+?)\/(.+\.$ext)$/i;
    $location = $thefile;
    $annot_text = $extra_text{$title};

my $image_json = <<"END_IMAGE_JSON";
  {
   "location": "+/$location",
   "trip-text": "$trip_text",
   "annot-text": "$annot_text",
   "type": "image"
  }
END_IMAGE_JSON


	if (!$firstfile) {print $outfd ",\n";}
	else {$firstfile=0;}
	print $outfd $image_json;
}

sub process_video {
    my ($thefile, $isincurrdir, $ext) = @_;

	($text,$title) = $thefile =~ /^.+?\/(.+?)\/(.+\.$ext)$/i;
	$location = $thefile;

    if (exists $extra_text{$title}) {
        $text .= " - " . $extra_text{$title};
    }

	$Text::Wrap::separator="\n";
	$Text::Wrap::columns=53;
    $text = wrap("","",$text);

	$duration_string = `ffprobe -i "$location" -show_format -v quiet | grep duration`;
	my ($sec,$msec) = $duration_string =~ /duration=(\d+?)\.(\d\d\d)/;

	my $numlines=()=$text=~/(\n)/g;
	$numlines++;

	$subtitles_file = $location . ".srt";
	open ($subfile, ">$subtitles_file");
	for ($i=0; $i<=$sec; $i++) {
		print $subfile "".($i+1)."\n";
		if ($i<$sec) {
			print $subfile "00:00:$i,000 --> 00:00:".($i+1).",000\n";
		} elsif ($msec ne "000") {
			print $subfile "00:00:$i,000 --> 00:00:$i,$msec\n";
		}
		print $subfile "$text [$i"."s/$sec"."s]\n\n";
	}
	close ($subfile);

my $video_json = <<"END_VIDEO_JSON";
  {
   "location": "+/$location",
   "omx-subtitles": "+/$subtitles_file",
   "omx-subtitles-numlines": "$numlines",
   "type": "video"
  }
END_VIDEO_JSON

	if (!$firstfile) {print $outfd ",\n";}
        else {$firstfile=0;}
        print $outfd $video_json;
}


sub process_file {
	my ($thefile, $isincurrdir) = @_;

	print STDERR "Processing: $thefile...\n";

	if ($thefile =~ /^.+\.(jpe{0,1}g)$/i || $thefile =~ /^.+\.(png)$/i) {process_image ($thefile, $isincurrdir, $1);}
	elsif ($thefile =~ /^.+\.(mpe{0,1}g)$/i || $thefile =~ /^.+\.(avi)$/i || $thefile =~ /^.+\.(mp4)$/i || $thefile =~ /^.+\.(mov)$/i || $thefile =~ /^.+\.(m4v)$/i) {process_video ($thefile, $isincurrdir, $1);}
	else {print STDERR "****Error: Unknown file type for file: $thefile\n";}
}



if (scalar(@ARGV) < 2) {
	print STDERR "Usage: perl $0 <output file> <file or dir> [file or dir] ...\n\n";
	exit(1);
}

$outfile = $ARGV[0];
if (-d $outfile) {
	print STDERR "Error: Output file $outfile is a directory.\n";
	print STDERR "Usage: perl $0 <output file> <file or dir> [file or dir] ...\n\n";
	exit(1);
}

if ($ARGV[2] eq ".." || $ARGV[2] eq ".") {
	print STDERR "Error: Second input file is .. or .\n";
	exit(1);
}

#if (-e $outfile) {
	#print "Output file $outfile exists. Append or Overwrite? (A/O): ";
	#$oa = <STDIN>;
	#chomp $oa;

	#$oa = uc($oa);

	#if ($oa ne "O" && $oa ne "A") {
		#print STDERR "That is not one of the choices. Exiting.\n";
		#exit(1);
	#}
#}
$oa="A";

if ($oa eq "A") {
	system ("head --lines=-2 $outfile > $outfile.tmp");
	open ($outfd, ">>$outfile.tmp");
	$firstfile=0;
}

else {
	open ($outfd, ">$outfile");

print $outfd <<EOT;
{
 "issue": "1.3.5",
 "tracks": [
EOT

}

if (scalar(@ARGV) == 3 && $ARGV[2] eq "...") {
	$lsout = `ls -1dFrt media/* | grep -A 1000 "$ARGV[1]" | tail -n +2`;
	chomp $lsout;
	#$lsout =~ s/^/\"/;
	#$lsout =~ s/$/\"/;
	#$lsout =~ s/\n/\"\n\"/g;

	push (@ARGV, split(/\n/, $lsout));
}

foreach $fileordir (@ARGV[1 .. $#ARGV]) {

	if ($fileordir =~ /^(.+)\/$/) {$fileordir=$1;}
	if ($fileordir eq "..." || $fileordir eq ".." || $fileordir eq "." ) {next;}

	if (-d $fileordir) {
		process_dir ($fileordir);
	}

	else {
		get_extra_text($fileordir);
		process_file ($fileordir, 1);
		%extra_text=();
	}
}

print $outfd <<EOT;
 ]
}
EOT

close ($outfd);

if ($oa eq "A") {
	system ("mv $outfile.tmp $outfile");
}

