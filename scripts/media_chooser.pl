#!/usr/bin/perl
use warnings;
use strict;
use Tk;
use Tk::JPEG;
use List::Util qw(first);

#use utf8;
#use open ':encoding(utf8)';
#binmode(STDOUT, ":utf8");

my $GEOM = "1920x1080";
my $extradir = "/home/joshi/digital_media_frame_touch/unprocessed_pics/extra";

if (scalar(@ARGV) != 1) {
	print STDERR "Needs one argument.\n";
	exit();
}

my $dir = $ARGV[0];
if ($dir =~ /^(.+)\/$/) {$dir = $1;}

my $mw = new MainWindow;
$mw->geometry ("1920x1080");
my @files = <"$dir/*">;
@files = sort grep {$_ =~ /jpe{0,1}g$/i || $_ =~ /png$/i || $_ =~ /mpe{0,1}g$/i || $_ =~ /avi$/i || $_ =~ /mp4$/i || $_ =~ /mov$/i} @files;

my $filenum=0;
my $shot;
my $button;
my $entry;
my $entry2;
my $next;
my $extra_text="";
my $filename="";
my $kept=0;
my $fr1;
my $fr2;
my $l1;
my $l2;
my $l3;
my $l4;
my $l5;
my $l6;
my $l7;
my $l8;
my $skipped=0;
my $basename;
my %ethash;
my $moved=0;
my $city="";
my $region="";
my $subregion="";
my $country="";
my $gps="";
my $prevtxt="";
my ($deg1,$min1,$sec1,$dir1);
my ($deg2,$min2,$sec2,$dir2);
my ($lat, $lon, $latnum, $lonnum);

sub next_image {
	my ($todo) = @_;
	my ($bn) = $files[$filenum] =~ /.+\/(.+)$/;
	my $et;

	if ($todo eq "keep") {
        $extra_text = $entry->Contents;
        chomp $extra_text;
        $extra_text =~ s/\n+$//;

		if ($extra_text ne "") {
			$extra_text =~ s/[\\\`]//g;
			$extra_text =~ s/\"/\'/g;
            $extra_text =~ s/\n+$//;
            $extra_text =~ s/^\n//;
            $extra_text =~ s/(\S)\n(\S)/$1$2/g;
            $extra_text =~ s/\n/ /g;
            $extra_text =~ s/  / /g;

			open ($et, ">> :encoding(UTF-8)", "$dir/extra_text.txt");
			print $et "$bn\n$extra_text\n";
			close ($et);
		}

        $prevtxt = $extra_text;

		$kept++;
	}

	elsif ($todo eq "skip") {
		system ("trash \"$files[$filenum]\"");
		$skipped++;
	}

    elsif ($todo eq "move") {
        system ("mv \"$files[$filenum]\" $extradir");
        $moved++;
    }

	$filenum++;
	if ($filenum == scalar(@files)) {
		if ($kept == 0) {system ("rmdir \"$dir\"");}
		exit();
	}

	($basename) = $files[$filenum] =~ /^.+\/(.+?)$/;

	$shot->blank;
	$extra_text="";
	$entry->Contents("");
    $entry2->Contents($prevtxt);
	if (exists $ethash{$basename}) {$entry->Contents ($ethash{$basename});}
	$entry->focus;

	if ($files[$filenum] =~ /jpe{0,1}g$/i) {$filename = $files[$filenum];}
	else {$filename = "web-video-icon.jpg";}

    $city="";
    $region="";
    $subregion="";
    $country="";
    $gps="";

    open(my $info, "~/bin/Image-ExifTool-12.98/exiftool \"$files[$filenum]\" |");
    while (<$info>) {
        chomp;
        #if (/GPS Position\s+: (.+)/) {$gps=$1; $gps=~s/deg/°/g; $gps=~s/ //g; $gps=~s/,/ /;}
        if (/GPS Position\s+: (.+?), (.+)/) {
            #print "$1\n$2\n";

            $lat = $1;
            $lon = $2;

            ($deg1,$min1,$sec1,$dir1) = $lat =~ /^(\d+) deg (\d+)' (.+?)" (\w)/;
            ($deg2,$min2,$sec2,$dir2) = $lon =~ /^(\d+) deg (\d+)' (.+?)" (\w)/;

            $latnum = ($deg1 + ($min1/60) + ($sec1/3600)) * ($dir1 =~ /[WS]/ ? -1 : 1);
            $lonnum = ($deg2 + ($min2/60) + ($sec2/3600)) * ($dir2 =~ /[WS]/ ? -1 : 1);

            $gps = "$latnum, $lonnum";
            #print "$gps\n";
        }
    }
    close($info);

    open(my $info2, "~/bin/Image-ExifTool-12.98/exiftool -api geolocation \"-geolocation*\"  \"$files[$filenum]\" |");
    while (<$info2>) {
        chomp;
        if (/Geolocation City\s+: (.+)/) {$city=$1;}
        if (/Geolocation Region\s+: (.+)/) {$region=$1;}
        if (/Geolocation Subregion\s+: (.+)/) {$subregion=$1;}
        if (/Geolocation Country\s+: (.+)/) {$country=$1;}
    }
    close($info2);


	$l1->configure (-text => "File ".($filenum+1)."/".scalar(@files));
	$l2->configure (-text => "Kept: $kept   Skipped: $skipped    Moved: $moved");
	$l3->configure (-text => $basename);
    $l4->configure (-text=>"City: $city");
    $l5->configure (-text=>"Region: $region");
    $l6->configure (-text=>"Sub: $subregion");
    $l7->configure (-text=>"Country: $country");
    $l8->delete("1.0","end");
    $l8->Insert($gps);

	$shot->read($filename);
	$mw->update;

	if ($files[$filenum] =~ /mpe{0,1}g$/i || $files[$filenum] =~ /avi$/i || $files[$filenum] =~ /mp4$/i || $files[$filenum] =~ /mov$/i || $files[$filenum] =~ /mkv$/i) {
		print ("mpv \"$files[$filenum]\" 2> /dev/null");
		system ("mpv \"$files[$filenum]\" 2> /dev/null");
	}
}


sub redo_image {
	if ($files[$filenum] !~ /jpe{0,1}g$/i && $files[$filenum] !~ /png$/i) {return;}

	my ($deg) = @_;

	my $origfile = $files[$filenum];
	$origfile =~ s/^media/\/data\/Pictures/;
	$origfile =~ s/\.resized//;

	if (!-e $origfile) {
		print STDERR "Error: Cannot find original file: $origfile\n";
		return;
	}

	system ("cp \"$origfile\" \"$files[$filenum]\"");

	#system ("eog \"$files[$filenum]\"");
	system ("exifautotran \"$files[$filenum]\"");
	system ("convert -rotate $deg -resize $GEOM \"$files[$filenum]\" \"$files[$filenum]\"");
	$shot->blank;
	$shot->read($files[$filenum]);
        $mw->update;
}



my $trf1 = `ls "$dir" | grep -E "resized|rotated"`;
chomp $trf1;
my $trf2 = `find "$dir" -type l`;
chomp $trf2;
if ($trf1 eq "" && $trf2 eq "") {
	print STDERR "No resized images or video files found. Need to transform perhaps. Exiting.\n";
	exit(1);
}

my ($etf, $etext, $fn);
my $tmpfn;
if (-e "$dir/extra_text.txt") {
	open ($etf, "<$dir/extra_text.txt");
	while ($fn=<$etf>) {
		chomp $fn;
		$etext = <$etf>;
		chomp $etext;

		$ethash{$fn} = $etext;
        $tmpfn = $fn;
#print "$fn\n$etext\n";
	}
	close ($etf);

#print "$dir/$fn\n";
    $filenum = first { $files[$_] eq "$dir/$tmpfn" } 0..$#files;
    $filenum++;

	#system ("rm \"$dir/extra_text.txt\"");
}

if ($files[$filenum] =~ /jpe{0,1}g$/i || $files[$filenum] =~ /png$/i) {$filename = $files[$filenum];}
else {$filename = "web-video-icon.jpg";}

($basename) = $files[$filenum] =~ /^.+\/(.+?)$/;

# make one Photo object and one Button and reuse them.
$fr1 = $mw->Frame()->pack(-side=>"left");
$shot = $fr1->Photo(-file => "$filename", -format => "jpeg", width=>1440); #get first one
$button = $fr1->Button(-image => $shot)->pack(-anchor=>"sw", -side=>"left", -expand=>1, -fill=>"both");
# $button = $fr1->Scrolled("Button", -scrollbars=>"s", -image => $shot)->pack();

$fr2 = $mw->Frame()->pack(-side=>"right");
$entry = $fr2->Text(-width => 35, -height => 4, -wrap => "word", -font => "helvetica 20")->pack();
$entry->bind("<Return>" => sub {next_image ("keep");});
if (exists $ethash{$basename}) {$entry->Contents ($ethash{$basename});}

$gps="";
open(my $info, "~/bin/Image-ExifTool-12.98/exiftool \"$files[$filenum]\" |");
while (<$info>) {
    chomp;
    #if (/GPS Position\s+: (.+)/) {$gps=$1; $gps=~s/deg/°/g; $gps=~s/ //g; $gps=~s/,/ /;}
    if (/GPS Position\s+: (.+?), (.+)/) {
        #print "$1\n$2\n";

        $lat = $1;
        $lon = $2;

        ($deg1,$min1,$sec1,$dir1) = $lat =~ /^(\d+) deg (\d+)' (.+?)" (\w)/;
        ($deg2,$min2,$sec2,$dir2) = $lon =~ /^(\d+) deg (\d+)' (.+?)" (\w)/;

        $latnum = ($deg1 + ($min1/60) + ($sec1/3600)) * ($dir1 =~ /[WS]/ ? -1 : 1);
        $lonnum = ($deg2 + ($min2/60) + ($sec2/3600)) * ($dir2 =~ /[WS]/ ? -1 : 1);

        $gps = "$latnum, $lonnum";
        #print "$gps\n";
    }
}
close($info);

open(my $info2, "~/bin/Image-ExifTool-12.98/exiftool -api geolocation \"-geolocation*\"  \"$files[$filenum]\" |");
while (<$info2>) {
    chomp;
    if (/Geolocation City\s+: (.+)/) {$city=$1;}
    if (/Geolocation Region\s+: (.+)/) {$region=$1;}
    if (/Geolocation Subregion\s+: (.+)/) {$subregion=$1;}
    if (/Geolocation Country\s+: (.+)/) {$country=$1;}
}
close($info2);



$l1 = $fr2->Label(-text=>"File ".($filenum+1)."/".scalar(@files), -font => "helvetica 20")->pack();
$l2 = $fr2->Label(-text=>"Kept: $kept   Skipped: $skipped   Moved: $moved", -font => "helvetica 20")->pack();
$l3 = $fr2->Label(-text=>$basename, -font => "helvetica 20")->pack();
$l4 = $fr2->Label(-text=>"City: $city", -font => "helvetica 20")->pack();
$l5 = $fr2->Label(-text=>"Region: $region", -font => "helvetica 20")->pack();
$l6 = $fr2->Label(-text=>"Sub: $subregion", -font => "helvetica 20")->pack();
$l7 = $fr2->Label(-text=>"Country: $country", -font => "helvetica 20")->pack();
$l8 = $fr2->Text(-width => 35, -height => 1, -font => "helvetica 15")->pack();
$l8->Insert($gps);

$next = $fr2->Button(-text => "Skip", -command=> sub {next_image ("skip");})->pack(-expand=>1, -fill=>"both");
$mw->bind('<Control-Key-z>', sub {next_image ("skip");});

#my $redo1 = $fr2->Button(-text => "Rotate image 90 degrees clockwise", -command=> sub {redo_image(90);})->pack(-expand=>1, -fill=>"both");
#my $redo2 = $fr2->Button(-text => "Rotate image 90 degrees counter-clockwise", -command=> sub {redo_image(270);})->pack(-expand=>1, -fill=>"both");
my $mvex = $fr2->Button(-text => "Move to extra", -command=> sub {next_image ("move");})->pack(-expand=>1, -fill=>"both");
# $mw->bind('<Control-Key-x>', sub {redo_image(90);});
# $mw->bind('<Control-Key-b>', sub {redo_image(270);});

$entry2 = $fr2->Text(-width => 35, -height => 4, -wrap => "word", -font => "helvetica 20")->pack();

$entry->focus;
$mw->update;

if ($files[$filenum] !~ /jpe{0,1}g$/i && $files[$filenum] !~ /png$/i) {system ("mpv \"$files[$filenum]\" 2> /dev/null");}

$mw->MainLoop;
