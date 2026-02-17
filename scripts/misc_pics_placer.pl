#!/usr/bin/perl
use warnings;
use strict;
use Tk;
use Tk::JPEG;
use utf8;
use List::MoreUtils;

my $GEOM = "1920x1080";
my $MEDIADIR = "/home/joshi/digital_media_frame_touch/media";
my $extradir = "/home/joshi/digital_media_frame_touch/unprocessed_pics/extra";

my $gps="";
my ($deg1,$min1,$sec1,$dir1);
my ($deg2,$min2,$sec2,$dir2);
my ($lat, $lon, $latnum, $lonnum);


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
my $next;
my $extra_text="";
my $filename="";
my $kept=0;
my $fr1;
my $fr2;
my $l1;
my $l2;
my $l3;
my $l8;
my $lb;
my $skipped=0;
my $basename;
my %ethash;
my @elements;

sub next_image {
	my ($todo) = @_;
	my ($bn) = $files[$filenum] =~ /.+\/(.+)$/;
	my $et;
	my @selected_index;

	if ($todo eq "keep") {
		@selected_index = $lb->curselection();
		if (scalar(@selected_index) == 0) {
		    print STDERR "ERROR: No directory selected.\n";
		    return;
		}
		@elements = $lb->get(0, 'end');

		if ($extra_text ne "") {
			$extra_text =~ s/[\\\`]//g;
			$extra_text =~ s/\"/\'/g;

			print "putting '$extra_text' into $elements[$selected_index[0]]/extra_text.txt\n";
			open ($et, ">> :encoding(UTF-8)", "$MEDIADIR/$elements[$selected_index[0]]/extra_text.txt");
			print $et "$bn\n$extra_text\n";
			close ($et);
		}

		system ("mv \"$dir/$bn\" \"$MEDIADIR/$elements[$selected_index[0]]\"");
		$kept++;
	}

    elsif ($todo eq "move") {
        system ("mv \"$files[$filenum]\" $extradir");
    }

	elsif ($todo eq "skip") {
		system ("trash \"$files[$filenum]\"");
		$skipped++;
	}

	$filenum++;
	if ($filenum == scalar(@files)) {
		if ($kept == 0) {system ("rmdir \"$dir\"");}
		exit();
	}

	($basename) = $files[$filenum] =~ /^.+\/(.+?)$/;

	$shot->blank;
	$extra_text="";
	$entry->delete(0,"end");
	if (exists $ethash{$basename}) {$entry->insert (0, $ethash{$basename});}
	$entry->focus;

	if ($files[$filenum] =~ /jpe{0,1}g$/i) {$filename = $files[$filenum];}
	else {$filename = "/home/joshi/digital_media_frame_touch/nik-presents/scripts/web-video-icon.jpg";}

	$l1->configure (-text => "File ".($filenum+1)."/".scalar(@files));
	$l2->configure (-text => "Kept: $kept   Skipped: $skipped");
	$l3->configure (-text => $basename);
    $gps = get_lat_lon($files[$filenum]);
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

@elements = $lb->get(0, 'end');	#system ("eog \"$files[$filenum]\"");
	system ("exifautotran \"$files[$filenum]\"");
	system ("convert -rotate $deg -resize $GEOM \"$files[$filenum]\" \"$files[$filenum]\"");
	$shot->blank;
	$shot->read($files[$filenum]);
        $mw->update;
}


sub save_to_select {
    my ($savedir) = @_;
    @elements = $lb->get(0, 'end');

    #print "$savedir\n". join("\n",@elements). "\n";
    my $diridx=0;
    my $lbitem;

    foreach $lbitem (@elements) {
        if ($lbitem eq $savedir) {
            last;
        }
        $diridx++;
    }

    # $diridx = firstidx {defined && $_ eq $savedir} @elements;
    $lb->selectionClear(0, "end");
    $lb->selectionSet($diridx);
    next_image ("keep");
}

sub get_lat_lon {
    my ($fname) = @_;
    $gps="";
    open(my $info, "~/bin/Image-ExifTool-12.98/exiftool \"$fname\" |");
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

    return($gps);
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
if (-e "$dir/extra_text.txt") {
	open ($etf, "< :encoding(UTF-8)", "$dir/extra_text.txt");
	while ($fn=<$etf>) {
		chomp $fn;
		$etext = <$etf>;
		chomp $etext;

		$ethash{$fn} = $etext;
	}
	close ($etf);

	system ("rm \"$dir/extra_text.txt\"");
}

if ($files[$filenum] =~ /jpe{0,1}g$/i || $files[$filenum] =~ /png$/i) {$filename = $files[$filenum];}
else {$filename = "/home/joshi/digital_media_frame_touch/nik-presents/scripts/web-video-icon.jpg";}

($basename) = $files[$filenum] =~ /^.+\/(.+?)$/;

# make one Photo object and one Button and reuse them.
$fr1 = $mw->Frame()->pack(-side=>"left");
$shot = $fr1->Photo(-file => "$filename", -format => "jpeg", width=>1440); #get first one
$button = $fr1->Button(-image => $shot)->pack(-anchor=>"sw", -side=>"left", -expand=>1, -fill=>"both");
# $button = $fr1->Scrolled("Button", -scrollbars=>"s", -image => $shot)->pack();$listbox->selectionSet(first, ?last?) 

$fr2 = $mw->Frame()->pack(-side=>"right");
$entry = $fr2->Entry(-width => 35, -textvariable=>\$extra_text, -font => "helvetica 20")->pack();
$entry->bind("<Return>" => sub {next_image ("keep");});
if (exists $ethash{$basename}) {$entry->insert (0, $ethash{$basename});}

$l1 = $fr2->Label(-text=>"File ".($filenum+1)."/".scalar(@files), -font => "helvetica 20")->pack();
$l2 = $fr2->Label(-text=>"Kept: $kept   Skipped: $skipped", -font => "helvetica 20")->pack();
$l3 = $fr2->Label(-text=>$basename, -font => "helvetica 20")->pack();

$gps = get_lat_lon($files[$filenum]);

print "GPS: $gps\n";

$l8 = $fr2->Text(-width => 35, -height => 1, -font => "helvetica 15")->pack();
$l8->Insert($gps);

my $keep2 = $fr2->Button(-text => "Save to Misc", -command=> sub {save_to_select ("Misc");})->pack(-expand=>1, -fill=>"both");
my $keep3 = $fr2->Button(-text => "Save to Welding Projects", -command=> sub {save_to_select ("Welding Projects");})->pack(-expand=>1, -fill=>"both");

my $keep = $fr2->Button(-text => "Save", -command=> sub {next_image ("keep");})->pack(-expand=>1, -fill=>"both");
my $mvex = $fr2->Button(-text => "Move to extra", -command=> sub {next_image ("move");})->pack(-expand=>1, -fill=>"both");

# $next = $fr2->Button(-text => "Skip", -command=> sub {next_image ("skip");})->pack(-expand=>1, -fill=>"both");
$mw->bind('<Control-Key-z>', sub {next_image ("skip");});

$lb = $fr2->Scrolled("Listbox", -selectmode => "single", -width=>50, -scrollbars => "e", -height=>40, -exportselection=>"False")->pack();
opendir my $dfh, "$MEDIADIR";
#foreach my $d (readdir $dfh) {
#    print Encode::decode_utf8($d) . "\n";
#}
my @folders = sort grep {$_ ne "." && $_ ne ".."} grep {-d "$MEDIADIR/$_"} readdir $dfh;

my @folders_utf;
foreach my $d (@folders) {
    push(@folders_utf, Encode::decode_utf8($d));
}

closedir $dfh;
$lb->insert('end', @folders_utf);

# my $redo1 = $fr2->Button(-text => "Rotate image 90 degrees clockwise", -command=> sub {redo_image(90);})->pack(-expand=>1, -fill=>"both");
# my $redo2 = $fr2->Button(-text => "Rotate image 90 degrees counter-clockwise", -command=> sub {redo_image(270);})->pack(-expand=>1, -fill=>"both");
# $mw->bind('<Control-Key-x>', sub {redo_image(90);});
# $mw->bind('<Control-Key-b>', sub {redo_image(270);});

$entry->focus;
$mw->update;

if ($files[$filenum] !~ /jpe{0,1}g$/i && $files[$filenum] !~ /png$/i) {system ("mpv \"$files[$filenum]\" 2> /dev/null");}

$mw->MainLoop;
