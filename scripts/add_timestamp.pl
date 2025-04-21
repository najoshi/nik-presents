#!/usr/bin/perl

use Tk;
use File::Basename;
use File::Copy;

sub do_addts {

	my ($d,$m,$y) = (localtime)[3,4,5];
	$curr_ts = ($y+1900)."-".($m+1)."-$d";
	foreach $dir (@ARGV) {

		if ($dir =~ /^(.+)\/$/) {$dir = $1;}

		opendir (DIR, $dir);
		@thefiles = grep {-f} map {"$dir/$_"} readdir (DIR);
		closedir (DIR);

		foreach $file (@thefiles) {
			$bn = fileparse($file);
			move ($file, "$dir/$curr_ts"."_$bn");
		}
	}
}


my $mw = MainWindow->new();
$mw->optionAdd('*font', 'Helvetica 20');

$mw->Label(-text => "Really add date to filenames?")->pack (-expand => 1, -fill => 'both');

$mw->Button (
        -text => 'OK',
        -command => sub {do_addts(); exit();},
)->pack (-expand => 1, -fill => 'both');

$mw->Button (
        -text => 'Cancel',
        -command => sub {exit();},
)->pack (-expand => 1, -fill => 'both');

MainLoop;

